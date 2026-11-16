// __multiversion__
// This signals the loading code to prepend either #version 100 or #version 300 es as apropriate.
// 厨锅的汤面（片元）：照 Diegesis 的 LiquidRenderer 逐格算。
// 清水是一张平的面（surface）：贴着锅壁一圈亮线，斜着看映出天色；锅里有料、烧热之后是 16 x 16 格的一张（mottled）：
// 每格按随汤转动的噪声分 7 档明暗，靠壁一圈偏亮，沿壁两格按节拍翻沫。颜色和各项强弱由脚本每帧经
// SetBlockEntityExtraUniforms 给（Compat/Diegesis 的厨锅场景）。贴图 32 x 512（tools/gen_pot_broth.py）：左 16 列是 Diegesis 的
// liquid.png（32 帧，每帧 0.1 秒），第 16..23 列从上到下是六张 8 x 8 的碎料图案。同一个骨骼里的碎料面片也走这里：
// 位置、图案号、颜色由顶点着色器算好（v_piece / v_tint），这里只取图案的一格、染色。
precision highp float;

#include "fragmentVersionCentroidUV.h"
#include "uniformEntityConstants.h"
#include "uniformPerFrameConstants.h"
#include "uniformShaderConstants.h"
#include "util.h"

LAYOUT_BINDING(0) uniform sampler2D TEXTURE_0;

// (r, g, b, a)：汤色与"浓度"（JE LiquidLook 的 ARGB，各 0..1）
uniform vec4 EXTRA_ACTOR_UNIFORM1;
// (mottle 的 255 档 + edgeBoil 的小数, 汤转过的弧度, 碎料的钟（顶点着色器用）, 液面比内胆中心高多少像素)
uniform vec4 EXTRA_ACTOR_UNIFORM2;
// 两个水波，每个两个数：位置（x、z 各按 1/16 像素取整，x + 128 z）和"强度的百分数 + 年龄（秒，不到 1）"
uniform vec4 EXTRA_ACTOR_UNIFORM3;

varying vec4 light;
varying vec4 fogColor;
varying vec3 v_rel;
// 碎料：(图案里的 u, v, 图案号, 1)；汤面是 0
varying vec4 v_piece;
// 碎料：颜色和露出汤面多少
varying vec4 v_tint;

const float CELLS = 16.0;          // LiquidSim.WAKE_CELLS
const float HALF = 4.0;            // 内胆半宽（像素）
const float SURFACE_PATH = 0.85;
const float MOTTLE_SCALE = 0.6;
const float MOTTLE_DETAIL = 2.2;
const float MOTTLE_STEPS = 7.0;
const float MOTTLE_STRENGTH = 0.24;
const float SEETHE_BEAT = 5.0;
const float SEETHE_AT_WALL = 0.5;
const float SEETHE_INSIDE = 0.2;
const float SEETHE_LIGHT = 0.32;
const float FRAMES = 32.0;
// 水波：LiquidSim 的高度场在 0.6 的黏度下每秒走 15.6 像素、0.16 秒衰减一半，这里按一圈往外走的环来算坡度
const float WAVE_SPEED = 15.6;
const float WAVE_WIDTH = 1.1;
const float WAVE_FADE = 0.23;
const float WAVE_LIGHT = 6.0;      // MOTTLE_WAVE_LIGHT
const float WAVE_STEPS = 8.0;      // WAKE_STEPS
const vec2 LIGHT = vec2(-0.5, -0.6);   // 场景的光从镜头这一侧的左上方来（液面上的分量）
// 贴图的布局：整张 32 x 512，汤面的纹理占左半，碎料图案 8 x 8 一张、从第 16 列起往下排
const float SHEET_WIDE = 32.0;
const float SHEET_HIGH = 512.0;
const float BITS_U = 16.0;
const float BIT = 8.0;
const vec3 SKY = vec3(0.85, 0.93, 1.0);

float hash(vec2 p) {
	return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453);
}

float noise(vec2 p) {
	vec2 i = floor(p);
	vec2 f = fract(p);
	f = f * f * (3.0 - 2.0 * f);
	float near = mix(hash(i), hash(i + vec2(1.0, 0.0)), f.x);
	float far = mix(hash(i + vec2(0.0, 1.0)), hash(i + vec2(1.0, 1.0)), f.x);
	return mix(near, far, f.y);
}

vec2 waveSlope(vec2 p, vec2 wave) {
	float strength = floor(wave.y) / 100.0;
	if (strength < 0.02) {
		return vec2(0.0);
	}
	float age = fract(wave.y);
	vec2 d = p - (vec2(mod(wave.x, 128.0), floor(wave.x / 128.0)) / 16.0 - HALF);
	float r = length(d);
	float off = r - WAVE_SPEED * age;
	float ring = exp(-off * off / (2.0 * WAVE_WIDTH * WAVE_WIDTH));
	float amount = strength * exp(-age / WAVE_FADE) * ring * off / (WAVE_WIDTH * WAVE_WIDTH);
	return r > 0.001 ? d / r * amount : vec2(0.0);
}

// 环的坡朝着光的一侧亮、背着的一侧暗，和整张面一样分档
vec3 waveLit(vec3 rgb, vec2 p) {
	vec2 slope = waveSlope(p, EXTRA_ACTOR_UNIFORM3.xy) + waveSlope(p, EXTRA_ACTOR_UNIFORM3.zw);
	float lit = clamp(dot(slope, LIGHT) * WAVE_LIGHT, -0.3, 0.45);
	lit = floor(lit * WAVE_STEPS + 0.5) / WAVE_STEPS;
	return rgb * (1.0 + min(0.0, lit)) + (1.0 - rgb) * max(0.0, lit);
}

void main() {
	if (v_piece.w > 0.5) {
		// 一块碎料：图案的一格（灰度）乘它的颜色；图案外面是透明的，面下的那部分被汤盖住
		vec2 at = clamp(floor(v_piece.xy * BIT), 0.0, BIT - 1.0);
		float kind = floor(v_piece.z + 0.5);
		vec4 bit = texture2D(TEXTURE_0, vec2((BITS_U + at.x + 0.5) / SHEET_WIDE, (kind * BIT + at.y + 0.5) / SHEET_HIGH));
		vec4 piece = vec4(v_tint.rgb * bit.rgb * light.rgb, bit.a * v_tint.a);
		piece.rgb = mix(piece.rgb, fogColor.rgb, fogColor.a);
		gl_FragColor = piece;
		return;
	}

	vec3 tint = EXTRA_ACTOR_UNIFORM1.rgb;
	float clearness = log(max(1.0 - EXTRA_ACTOR_UNIFORM1.a, 0.002));
	float mottle = floor(EXTRA_ACTOR_UNIFORM2.x) / 255.0;
	float turned = EXTRA_ACTOR_UNIFORM2.y;
	float edgeBoil = fract(EXTRA_ACTOR_UNIFORM2.x);
	float above = EXTRA_ACTOR_UNIFORM2.w;

	// 几何里汤面的贴图坐标只占左上四分之一（右边留给碎料的面片）
	vec2 q = clamp(uv * 2.0, 0.0, 0.9999);
	vec2 p = q * (2.0 * HALF) - HALF;                  // 这一点离锅心多远（像素）
	vec3 rgb;
	float alpha = 1.0 - exp(clearness * SURFACE_PATH);

	if (mottle > 0.01 || edgeBoil > 0.01) {
		vec2 cell = floor(q * CELLS);
		vec2 m = (cell + 0.5) / CELLS * (2.0 * HALF) - HALF;
		// 噪声倒着转回去读：斑块跟着汤和漂着的东西一起转
		float c = cos(turned);
		float s = sin(turned);
		vec2 sp = vec2(m.x * c + m.y * s, m.y * c - m.x * s);
		float value = 0.65 * noise(sp * MOTTLE_SCALE) + 0.35 * noise(sp * MOTTLE_DETAIL + vec2(7.0, 3.0));
		float stepped = floor(value * MOTTLE_STEPS + 0.5) / MOTTLE_STEPS - 0.5;
		float middle = 1.0 - max(abs(m.x), abs(m.y)) / HALF;
		rgb = tint * (1.0 + stepped * mottle * MOTTLE_STRENGTH * 2.0 + middle * mottle * 0.12);
		float fromWall = min(min(cell.x, cell.y), min(CELLS - 1.0 - cell.x, CELLS - 1.0 - cell.y));
		if (fromWall < 0.5) {
			rgb += (1.0 - rgb) * 0.2;
			alpha += 0.15;
		}
		if (fromWall < 1.5 && edgeBoil > 0.01) {
			// 每格各有各的节拍：沫是抖的，不是一起闪
			float spot = cell.y * CELLS + cell.x;
			float beat = floor(TIME * SEETHE_BEAT + hash(vec2(spot, 5.0)) * 7.0);
			float chance = edgeBoil * (fromWall < 0.5 ? SEETHE_AT_WALL : SEETHE_INSIDE);
			if (hash(vec2(spot, beat)) < chance) {
				rgb += (1.0 - rgb) * SEETHE_LIGHT;
			}
		}
		rgb = waveLit(rgb, m);
	} else {
		float facing = abs(normalize(v_rel).y);
		float grazing = 1.0 - facing;
		float fresnel = 0.04 + 0.96 * grazing * grazing * grazing * grazing;
		float sky = fresnel * 0.75;
		rgb = tint * 1.06 * (1.0 - sky) + SKY * sky;
		alpha += fresnel * 0.4;
		// 液面爬上锅壁的那道亮线：最外 14% 渐亮
		float rim = clamp((max(abs(p.x), abs(p.y)) / HALF - 0.86) / 0.14, 0.0, 1.0);
		rgb += (1.0 - rgb) * 0.45 * rim;
		alpha += 0.22 * rim;
		rgb = waveLit(rgb, p);
	}

	// 贴图按位置取：16 像素见方的一帧盖住整个内胆还有余，只露出中间一块
	vec2 guv = clamp(vec2(0.5 + (p.x + p.y * 0.5) / 16.0, 0.5 + (p.y + above) / 16.0), 0.02, 0.98);
	float frame = floor(mod(TIME * 10.0, FRAMES));
	vec4 grain = texture2D(TEXTURE_0, vec2(guv.x * 0.5, (guv.y + frame) / FRAMES));

	vec4 color = vec4(min(rgb, vec3(1.0)) * grain.rgb, clamp(alpha, 0.0, 1.0) * grain.a);
	color.rgb *= light.rgb;
	color.rgb = mix(color.rgb, fogColor.rgb, fogColor.a);
	gl_FragColor = color;
}
