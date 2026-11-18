# -*- coding: utf-8 -*-
# runner: py3
"""tools/gen_tatami.py：方块 JSON 的 states / permutations、转角贴图、terrain_texture 登记都是最新的；
工具里抄的 JE 方块状态和模型（blockstates/tatami.json、models/block/tatami_odd / tatami_even / tatami_half）和 JE 原文件一字不差。"""
from __future__ import print_function

import importlib.util
import io
import json
import os
import subprocess
import sys

import fdtest

TOOL = os.path.join(fdtest.ROOT, "tools", "gen_tatami.py")
JE = os.path.join(fdtest.ROOT, ".refs", "FarmersDelight", "src")
JE_STATES = os.path.join(JE, "generated", "resources", "assets", "farmersdelight", "blockstates", "tatami.json")
JE_MODELS = (os.path.join(JE, "main", "resources", "assets", "farmersdelight", "models", "block"),
             os.path.join(JE, "generated", "resources", "assets", "farmersdelight", "models", "block"))


def _tool():
    spec = importlib.util.spec_from_file_location("gen_tatami", TOOL)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _readJson(path):
    with io.open(path, encoding="utf-8") as f:
        return json.load(f)


def _model(name):
    for folder in JE_MODELS:
        path = os.path.join(folder, name + ".json")
        if os.path.isfile(path):
            return _readJson(path)
    raise AssertionError("JE 没有模型 " + name)


def testGeneratedFilesAreCurrent():
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    result = subprocess.run([sys.executable, TOOL, "--check"], capture_output=True, env=env)
    assert result.returncode == 0, result.stdout.decode("utf-8", "replace") + "\n先跑 py -3 tools/gen_tatami.py"


def testTheJavaDataInTheToolIsJavasOwn():
    if not os.path.isfile(JE_STATES):
        print("跳过：没有 JE 的资源（.refs/FarmersDelight）")
        return
    tool = _tool()
    variants = {}
    for key, variant in _readJson(JE_STATES)["variants"].items():
        values = dict(part.split("=") for part in key.split(","))
        model = variant["model"].split("/")[-1]
        variants[(values["facing"], values["paired"] == "true")] = (model, variant.get("x", 0), variant.get("y", 0))
    assert variants == tool.JE_VARIANTS
    for name in ("tatami_odd", "tatami_even"):
        faces = _model(name)["elements"][0]["faces"]
        assert dict((face, (spec["texture"].lstrip("#"), spec.get("rotation", 0))) for face, spec in faces.items()) == tool.JE_MODELS[name], name
        assert all(spec["uv"] == [0, 0, 16, 16] for spec in faces.values()), name
    half = _model("tatami_half")
    assert half["parent"] == "minecraft:block/cube_all" and half["textures"] == {"all": "farmersdelight:block/tatami_mat_half"}
    assert set(tool.JE_MODELS["tatami_half"].values()) == {("single", 0)}


if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
