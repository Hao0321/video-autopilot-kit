"""Command and fixture boundary; host globals remain explicitly injected."""
from __future__ import annotations

def _self_test(_host) -> None:
    caps = [(0, 2, "AI 教學先看結果"), (7, 9, "為什麼會失敗"), (15, 17, "三個步驟")]
    a = _host['plan_visual_rhythm'](28, caps, "auto", seed=7)
    b = _host['plan_visual_rhythm'](28, caps, "auto", seed=7)
    assert a == b and a["domain"] == "ai" and a["version"] == 9
    assert a["template_system"]["style"] == "cyan_lab"
    assert a["aesthetic_system"]["primary_family"] == "cobalt_lime_ui"
    assert a["caption_system"]["profile"] == "shorts_semantic_kinetic"
    assert a["color_system"]["profile"] == "ai_cobalt_crisp"
    assert a["color_system"]["stage"] == "source_before_graphics"
    assert a["trend_system"]["dominant_signal"] == "connectioneering"
    assert a["high_information_system"]["status"] == "AWAITING_EVIDENCE"
    assert a["three_d_system"]["status"] == "DOWNGRADED"
    assert a["programmatic_runtime"]["scope"] == "all_formats_all_domains"
    assert a["programmatic_runtime"]["implementation"] == "self_authored"
    assert a["three_d_system"]["requested_route"] == "data_space"
    assert a["shot_selection"]["status"] == "STYLE_CHOICE_REQUIRED"
    assert not _host['validate_visual_plan'](a)
    selected_style = _host['plan_visual_rhythm'](28, caps, "auto", seed=7, shot_style="vlog")
    assert selected_style["shot_selection"]["style_id"] == "vlog"
    assert selected_style["shot_selection"]["status"] == "AWAITING_SHOT_EVIDENCE"
    assert not _host['validate_visual_plan'](selected_style)
    assert _host['infer_domain']("拉麵只要 150 元") == "food"
    food = _host['plan_visual_rhythm'](28, [(0, 2, "傳統海鮮湯麵")], "food", seed=8)
    assert food["template_system"]["style"] == "food_heritage"
    toy = _host['plan_visual_rhythm'](28, [(0, 2, "戰鬥陀螺對決")], "toy", seed=9)
    assert toy["three_d_system"]["requested_route"] == "product_turntable"
    assert toy["three_d_system"]["effective_route"] == "verified_multiview_2d"
    assert _host['infer_domain']("重機試駕與過彎") == "automotive"
    assert _host['infer_domain']("與創辦人深度訪談") == "interview"
    interview = _host['PROFILES']["interview"]
    interview_blob = repr(interview)
    assert "two_shot" not in interview_blob and "speaker_close" not in interview_blob
    assert "approved_source" in interview_blob and "reaction face" in interview_blob
    assert _host['infer_domain']("手機相機盲測評測") == "product"
    long_plan = _host['plan_visual_rhythm'](240, [(0, 3, "紀錄片人物故事")], "documentary", seed=2)
    acts = {x["name"]: x for x in long_plan["energy_curve"]}
    assert long_plan["format"] == "longform" and acts["payoff"]["energy"] > acts["breath"]["energy"]
    assert long_plan["caption_system"]["profile"] == "longform_clean_locked"
    assert all(event["mode"] == "clean" for event in long_plan["caption_system"]["events"])
    value_plan = _host['plan_visual_rhythm'](
        45, [(0, 2, "$1 BILLION"), (8, 10, "$50 MILLION"), (13, 15, "$300 MILLION")],
        "business", seed="value-ladder",
    )
    assert value_plan["shot_dynamics_system"]["value_particle_overlay"]["enabled"]
    assert value_plan["shot_dynamics_system"]["value_particle_overlay"]["is_transition"] is False
    assert value_plan["shot_dynamics_system"]["value_ladder"]["beat_count"] == 3
    for key in _host['PROFILES']:
        p = _host['plan_visual_rhythm'](42, [(4, 7, "問題與結果"), (25, 28, "最後實測")], key, seed=key)
        assert p["domain"] == key and p["theme"] in _host['THEMES'] and not _host['validate_visual_plan'](p)
    with _host['tempfile'].TemporaryDirectory(prefix="visual-assets-") as temp_dir:
        output = _host['os'].path.join(temp_dir, "visual_plan.json")
        integrated = _host['write_visual_plan'](
            output, duration=24, captions=caps, genre="food", format="shorts",
            context_text="拉麵實測", seed="asset-hub",
        )
        assert integrated["programmatic_runtime"]["status"] == "GREEN"
        assert _host['os'].path.isfile(_host['os'].path.join(temp_dir, "current_composition.json"))
        assert _host['os'].path.isfile(_host['os'].path.join(temp_dir, "current_render_graph.json"))
        assert integrated["asset_intelligence"]["plan"] == _host['ASSET_PLAN_NAME']
        assert _host['os'].path.isfile(_host['os'].path.join(temp_dir, _host['ASSET_PLAN_NAME']))
        assert _host['os'].path.isfile(_host['os'].path.join(temp_dir, _host['PACKET_NAME']))
        long_output = _host['os'].path.join(temp_dir, "long_visual_plan.json")
        long_integrated = _host['write_visual_plan'](
            long_output, duration=120,
            captions=[{"start": 1, "end": 3, "text": "累積 12K PUBLIC_FIXTURE", "kind": "main"}],
            genre="ai", format="longform", context_text="AI 教學成果", seed="long-caption",
        )
        assert long_integrated["caption_system"]["emphasis_overlay_ass"] == \
            "current_emphasis_overlays.ass"
        assert _host['os'].path.isfile(_host['os'].path.join(temp_dir, "current_emphasis_overlays.ass"))
    print("visual_director self-test OK")
