// __multiversion__
// This signals the loading code to prepend either #version 100 or #version 300 es as apropriate.
// 厨锅的汤面（顶点）：骨骼变换、顶点光照、雾，另把"相机到顶点"的向量交给片元算掠射角。
// broth 骨骼里除了汤面还有 32 张小面片：煮好的汤里浮着的碎料。几何里它们是缩在锅心的 32 个点，这里照 Diegesis 的 LiquidPieces
// 把每一张撑开、摆到位（金角螺旋、随汤转、一块块从面下冒上来、长大），并挑好图案和颜色交给片元。
// 数由脚本给（Compat/Diegesis/PotModel.py，打包的办法和同一套算术的 Python 版在 Shared/Rules/PotPiecesLook.py）。
precision highp float;

#include "vertexVersionCentroidUV.h"

#include "uniformWorldConstants.h"
#include "uniformEntityConstants.h"
#include "uniformPerFrameConstants.h"
#ifdef USE_SKINNING
#include "uniformAnimationConstants.h"
#endif

// (r, g, b, a)：汤色与"浓度"
uniform vec4 EXTRA_ACTOR_UNIFORM1;
// (mottle 的 255 档 + edgeBoil 的小数, 汤转过的弧度, 碎料的钟 = limit 的 8 倍取整 * 128 + clock, 液面比内胆中心高多少像素)
uniform vec4 EXTRA_ACTOR_UNIFORM2;
// 四个配料槽：类 * 262144 + 18 位颜色；0 是空槽
uniform vec4 EXTRA_ACTOR_UNIFORM4;

#line 26

attribute highp vec4 POSITION;
attribute vec2 TEXCOORD_0;
attribute vec4 NORMAL;

#if defined(USE_SKINNING)
#ifdef MCPE_PLATFORM_NX
attribute uint BONEID_0;
#else
attribute float BONEID_0;
#endif
#endif

varying vec4 light;
varying vec4 fogColor;
varying vec3 v_rel;
// 碎料：(图案里的 u, v, 图案号, 1)；汤面的顶点是 0
varying vec4 v_piece;
// 碎料：颜色（乘过自己的深浅）和露出汤面多少（面下的被汤盖住）
varying vec4 v_tint;

// 几何的贴图坐标按 64 x 64 记：汤面在左上 32 x 32；碎料从 x = 32 起，8 x 8 一格、一行 4 格，每张面片占格子中间的 6 x 6
const float UV_UNITS = 64.0;
const float PIECES_U = 32.0;
const float PIECE_CELL = 8.0;
const float PIECE_COLUMNS = 4.0;
const float PIXEL = 0.0625;            // 一个模型像素是世界里的多少格
const float HALF = 4.0;                // 汤的内壁离锅心（像素）
// LiquidPieces 的数（PotPiecesPiece.py / PotPiecesLook.py，测试对着查）
const float PIECE_GOLDEN = 2.3999631;  // 金角：相邻两块转这么多
const float PIECE_OUTWARD = 0.7548777; // 向外的步长
const float PIECE_REACH = 0.9;         // 离壁至少留一成
const float PIECE_RATES = 20.0;        // 随汤转的快慢分这么多档
const float PIECE_STEP = 0.0823;       // 一块出发到下一块出发（秒）
const float PIECE_GROW = 0.16;         // 长大的半衰期（秒）
const float PIECE_RISE_TIME = 0.55;    // 从面下冒上来要多久
const float PIECE_RISE_DEPTH = 2.2;    // 从面下多深冒上来（像素）
const float PIECE_OVERSHOOT = 2.6;     // 冒上来的过冲
const float PIECE_LIFT = 0.16;         // 浮在面上方这么高
const float PIECE_PATH = 1.3;          // 面下的碎料隔着多少汤看（斜着看，比深度长）
const float LIMIT_STEPS = 8.0;
const float CLOCK_ROOM = 128.0;
const float CLASS_UNIT = 262144.0;
// CookedPieces 的数（PotPiecesKinds.py）
const float PIECE_BIG = 1.65;
const float PIECE_SMALL = 1.2;
const float PIECE_HERB = 1.3;
const float PIECE_FAT = 0.75;
const float PIECE_GRAIN = 0.75;
const float FAT_LIGHT = 0.55;
const vec3 EGG_WHITE = vec3(0.957, 0.945, 0.902);   // 0xF4F1E6
const vec3 EGG_YOLK = vec3(0.949, 0.761, 0.188);    // 0xF2C230
// 图案号：贴图里从上到下
const float COIN = 0.0;
const float CHUNK = 1.0;
const float NUGGET = 2.0;
const float SHRED = 3.0;
const float LEAF = 4.0;
const float DROP = 5.0;

float pieceRandom(float index, float salt) {
	return fract(sin(index * 12.9898 + salt * 78.233) * 43758.5453);
}

vec3 slotColor(float slot) {
	float rest = slot - floor(slot / CLASS_UNIT) * CLASS_UNIT;
	float red = floor(rest / 4096.0);
	float green = floor((rest - red * 4096.0) / 64.0);
	return vec3(red, green, rest - red * 4096.0 - green * 64.0) / 63.0;
}

// 第 index 块的这个角（corner 的两个分量各是 0 或 1）该在哪：离锅心 (x, 比液面高多少, z)，锅自己的坐标（像素）
vec3 pieceVertex(float index, vec2 corner) {
	float state = EXTRA_ACTOR_UNIFORM2.z;
	float limit = floor(state / CLOCK_ROOM) / LIMIT_STEPS;
	float clock = state - floor(state / CLOCK_ROOM) * CLOCK_ROOM;
	float age = max(clock - index, 0.0) * PIECE_STEP;
	float grown = clamp(limit - index, 0.0, 1.0) * (1.0 - exp2(-age / PIECE_GROW));

	// 这一块是哪个槽切出来的第几块，还是一滴油：各槽的块排成一列，每两块后面插一滴油，循环着用（PotPiecesLook.sourceOf）
	vec4 slots = EXTRA_ACTOR_UNIFORM4;
	vec4 classes = floor(slots / CLASS_UNIT);
	vec4 counts = step(0.5, classes) * (2.0 + step(1.5, classes) * step(classes, vec4(2.5)));   // 谷物三粒，别的两块
	float food = counts.x + counts.y + counts.z + counts.w;
	float drops = floor(food / 2.0);
	float total = max(food + drops, 1.0);
	float order = index - total * floor((index + 0.5) / total);
	float third = floor((order + 0.5) / 3.0);
	bool drop = order - third * 3.0 > 1.5 && third < drops - 0.5;
	float piece = order - min(drops, third);
	float slot = slots.x;
	float cls = classes.x;
	if (piece > counts.x - 0.5) {
		piece -= counts.x;
		slot = slots.y;
		cls = classes.y;
		if (piece > counts.y - 0.5) {
			piece -= counts.y;
			slot = slots.z;
			cls = classes.z;
			if (piece > counts.z - 0.5) {
				piece -= counts.z;
				slot = slots.w;
				cls = classes.w;
			}
		}
	}
	grown *= step(0.5, food);

	// 这一类切成什么（PotPiecesLook.CUTS）：图案、多宽、什么颜色
	bool first = piece < 0.5;
	float kind = NUGGET;
	float size = PIECE_SMALL;
	float solid = 1.0;
	vec3 color = slotColor(slot);
	if (drop) {
		kind = DROP;
		size = PIECE_FAT;
		solid = 0.0;
		color = mix(EXTRA_ACTOR_UNIFORM1.rgb, vec3(1.0), FAT_LIGHT);
	} else if (cls < 1.5) {            // 蛋：蛋白的丝、蛋黄的小块
		kind = first ? SHRED : NUGGET;
		size = first ? PIECE_HERB : PIECE_SMALL;
		color = first ? EGG_WHITE : EGG_YOLK;
	} else if (cls < 2.5) {            // 谷物：小粒
		size = PIECE_GRAIN;
	} else if (cls < 3.5) {            // 意面：丝
		kind = SHRED;
		size = PIECE_HERB;
	} else if (cls < 4.5) {            // 肉：大块、小块
		kind = first ? CHUNK : NUGGET;
		size = first ? PIECE_BIG : PIECE_SMALL;
	} else if (cls < 5.5) {            // 绿的：叶子、丝
		kind = first ? LEAF : SHRED;
		size = PIECE_HERB;
	} else if (first) {                // 其余：币、小块
		kind = COIN;
		size = PIECE_BIG * 0.9;
	}

	// 排在哪：金角螺旋，圆推到方壁的角上；随汤转，离心越远转得越快
	float reach = sqrt(0.06 + 0.94 * fract(index * PIECE_OUTWARD));
	float rate = floor((0.45 + 0.75 * reach) * PIECE_RATES + 0.5) / PIECE_RATES;
	float angle = index * PIECE_GOLDEN + EXTRA_ACTOR_UNIFORM2.y * rate;
	vec2 way = vec2(cos(angle), sin(angle));
	float drawn = size * grown;
	vec2 middle = way * (reach * PIECE_REACH / max(abs(way.x), abs(way.y))) * (HALF - drawn * 0.3);
	// 实心的随便朝哪边躺，油膜只偏一点（好让画在上面的亮边留在一侧）
	float yaw = solid > 0.5 ? pieceRandom(index, 1.0) * 6.2831853 : (pieceRandom(index, 1.0) - 0.5) * 0.9;
	vec2 arm = (corner - 0.5) * drawn;
	vec2 spot = middle + vec2(arm.x * cos(yaw) - arm.y * sin(yaw), arm.x * sin(yaw) + arm.y * cos(yaw));
	// 从面下冒上来，先冲过头再落回
	float back = min(age / PIECE_RISE_TIME, 1.0) - 1.0;
	float risen = 1.0 + (PIECE_OVERSHOOT + 1.0) * back * back * back + PIECE_OVERSHOOT * back * back;
	float lift = PIECE_LIFT + size * 0.1 - PIECE_RISE_DEPTH * (1.0 - risen);

	float mirrored = step(0.5, pieceRandom(index, 2.0));
	v_piece = vec4(mix(corner.x, 1.0 - corner.x, mirrored), corner.y, kind, 1.0);
	float clearness = log(max(1.0 - EXTRA_ACTOR_UNIFORM1.a, 0.002));
	v_tint = vec4(color * mix(0.9, 1.0, pieceRandom(index, 3.0)), exp(clearness * max(-lift, 0.0) * PIECE_PATH));
	return vec3(spot.x, lift, spot.y);
}

void main() {
	POS4 entitySpacePosition;
	POS4 entitySpaceNormal;

	// 碎料的面片在几何里缩在锅心、汤面的高度上：从那一点起挪多少（模型的轴，像素；几何的 x 是锅自己坐标的反号）
	v_piece = vec4(0.0);
	v_tint = vec4(0.0);
	vec3 shift = vec3(0.0);
	vec2 texel = TEXCOORD_0 * UV_UNITS;
	if (texel.x > PIECES_U + 0.5) {
		vec2 inCell = (texel - vec2(PIECES_U, 0.0)) / PIECE_CELL;
		vec2 cell = floor(inCell);
		vec3 spot = pieceVertex(cell.x + cell.y * PIECE_COLUMNS, step(0.5, inCell - cell));
		shift = vec3(-spot.x, spot.y, spot.z);
	}

#ifdef USE_SKINNING
#ifdef NETEASE_SKINNING
	MAT4 boneMat = GetBoneMatForNetease(int(BONEID_0));
#else
	#if defined(LARGE_VERTEX_SHADER_UNIFORMS)
	MAT4 boneMat = BONES[int(BONEID_0)];
	#else
	MAT4 boneMat = BONE;
	#endif
#endif
	entitySpacePosition = boneMat * POSITION;
	entitySpaceNormal = boneMat * NORMAL;
	// 挪的量按世界里的大小给：模型和骨骼矩阵里有没有缩放、顶点是什么单位都不用管
	vec3 moved = normalize(boneMat[0].xyz) * shift.x + normalize(boneMat[1].xyz) * shift.y + normalize(boneMat[2].xyz) * shift.z;
#else
	entitySpacePosition = POSITION * vec4(1.0, 1.0, 1.0, 1.0);
	entitySpaceNormal = NORMAL * vec4(1.0, 1.0, 1.0, 0.0);
	vec3 moved = shift;
#endif
	entitySpacePosition.xyz += moved * (PIXEL / length(WORLD[0].xyz));

	POS4 pos = WORLDVIEWPROJ * entitySpacePosition;
	gl_Position = pos;

	// 汤面永远朝上，按满的顶面亮度算（引擎在"有顶"的维度会把朝上的面当背光面压到 0.45，这里不跟）
	light = vec4(TILE_LIGHT_COLOR.xyz, 1.0);
	uv = TEXCOORD_0;
	// 世界矩阵的平移是相对相机的：这就是相机到顶点的向量（世界朝向）
	v_rel = (WORLD * entitySpacePosition).xyz;

	fogColor.rgb = FOG_COLOR.rgb;
	fogColor.a = clamp(((pos.z / RENDER_DISTANCE) - FOG_CONTROL.x) / (FOG_CONTROL.y - FOG_CONTROL.x), 0.0, 1.0);
}
