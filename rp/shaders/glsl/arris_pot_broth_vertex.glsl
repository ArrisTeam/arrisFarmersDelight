// __multiversion__
// This signals the loading code to prepend either #version 100 or #version 300 es as apropriate.
// 厨锅的汤面（顶点）：骨骼变换、顶点光照、雾，另把"相机到顶点"的向量交给片元算掠射角。
precision highp float;

#include "vertexVersionCentroidUV.h"

#include "uniformWorldConstants.h"
#include "uniformEntityConstants.h"
#include "uniformPerFrameConstants.h"
#ifdef USE_SKINNING
#include "uniformAnimationConstants.h"
#endif

#line 16

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

void main() {
	POS4 entitySpacePosition;
	POS4 entitySpaceNormal;

#ifdef USE_SKINNING
#ifdef NETEASE_SKINNING
	MAT4 boneMat = GetBoneMatForNetease(int(BONEID_0));
	entitySpacePosition = boneMat * POSITION;
	entitySpaceNormal = boneMat * NORMAL;
#else
	#if defined(LARGE_VERTEX_SHADER_UNIFORMS)
	entitySpacePosition = BONES[int(BONEID_0)] * POSITION;
	entitySpaceNormal = BONES[int(BONEID_0)] * NORMAL;
	#else
	entitySpacePosition = BONE * POSITION;
	entitySpaceNormal = BONE * NORMAL;
	#endif
#endif
#else
	entitySpacePosition = POSITION * vec4(1.0, 1.0, 1.0, 1.0);
	entitySpaceNormal = NORMAL * vec4(1.0, 1.0, 1.0, 0.0);
#endif

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
