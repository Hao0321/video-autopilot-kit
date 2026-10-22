"""Original public compiler policy controls; synthetic authority, no review or media."""
import hashlib
import importlib.util
import json
import math
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
SKILL = ROOT / "codex-skill" / "video-autopilot"
sys.path.insert(0, str(HERE))
from sync_canonical import _assert_public_design_bridge_contract, _copy_public_owned, _copy_text
from public_sync_inventory import PUBLIC_OWNED_PATHS

REQUEST = {"format":"longform", "domain":"general", "topic":"Original public policy contract fixture", "duration":3,
           "beats":[{"id":"public-context", "role":"chapter", "energy":0.2, "subject":"Original public policy contract fixture"}]}
AGENT = {"mode":"agent_reference_comparison", "authorization":"Synthetic public unit authority; not an artifact review."}

def policy_sha(policy):
    return hashlib.sha256(json.dumps(policy,ensure_ascii=False,sort_keys=True,separators=(",",":")).encode()).hexdigest()

def estimate_tokens(value):
    # Independent copy of the Kit's conservative CJK/JSON estimate (context_budget.estimate_tokens).
    text = json.dumps(value,ensure_ascii=False,separators=(",",":"))
    cjk = len(re.findall(r"[\u3400-\u9fff\uf900-\ufaff]",text))
    return cjk + math.ceil(max(0,len(text)-cjk)/4)

def assert_public_learning(case, learning, policy):
    # Editkin's Template Short composer binds this packet: a measured budget, the selected rule ids and the review mode.
    budget = learning["budget"]
    case.assertEqual(learning["knowledge_card"],[])
    case.assertEqual(learning["quality_95"]["review_mode"],policy["mode"])
    case.assertEqual(learning["quality_95"]["policy_sha256_12"],policy_sha(policy)[:12])
    case.assertEqual((budget["knowledge_rules_selected"],budget["knowledge_rules_trimmed"]),(0,0))
    case.assertIs(budget["within_budget"],True)
    case.assertEqual(budget["estimated_tokens"],estimate_tokens(learning))
    case.assertTrue(1 <= budget["estimated_tokens"] <= budget["max_tokens"] <= 1100)


class PublicDesignReviewPolicyTests(unittest.TestCase):
    def invoke(self, policy=None, skill=SKILL):
        args = [sys.executable,"-B","-X","utf8",str(skill / "editkin_design_bridge.py"),"--request-json",json.dumps(REQUEST)]
        if policy is not None:
            args += ["--review-policy-json",json.dumps(policy)]
        return subprocess.run(args,capture_output=True,text=True,encoding="utf-8",timeout=30,
                              creationflags=getattr(subprocess,"CREATE_NO_WINDOW",0))

    def assert_bound(self, brief, policy, actor):
        digest = policy_sha(policy)
        self.assertEqual(brief["reviewPolicy"],policy)
        self.assertEqual(brief["reviewPolicySha256"],digest)
        self.assertEqual(brief["request"],REQUEST)
        review = brief["context"]["review"]
        self.assertEqual(review["policy"],policy)
        self.assertEqual(review["policySha256"],digest)
        self.assertEqual(review["actor"],actor)
        self.assertEqual(review["checkpoint"],"agent_review" if actor=="agent" else "human_review")
        self.assertTrue(review["required"])
        self.assertFalse(review["completed"])
        self.assertIn("continuous_motion",review["requirements"])
        self.assertEqual(brief["context"]["profile"],"public-video-autopilot-design-v6")
        assert_public_learning(self,brief["context"]["learning"],policy)
        self.assertNotIn("craft",brief["context"])
        dependencies = {row["path"]:row["sha256"] for row in brief["sources"]}
        self.assertEqual(dependencies["review_policy.py"],hashlib.sha256((SKILL / "review_policy.py").read_bytes()).hexdigest())
        self.assertFalse(any("state.json" in name for name in dependencies))

    def test_actual_public_cli_normalizes_authorized_agent_envelope(self):
        command = self.invoke({**AGENT,"authorization":"  "+AGENT["authorization"]+"  "})
        self.assertEqual(command.returncode,0,command.stderr)
        self.assert_bound(json.loads(command.stdout),AGENT,"agent")

    def test_missing_and_explicit_human_policy_remain_human(self):
        missing, explicit = self.invoke(), self.invoke({"mode":"human"})
        self.assertEqual(missing.returncode,0,missing.stderr)
        self.assertEqual(explicit.returncode,0,explicit.stderr)
        self.assert_bound(json.loads(missing.stdout),{"mode":"human"},"human")
        self.assert_bound(json.loads(explicit.stdout),{"mode":"human"},"human")
        self.assertEqual(json.loads(missing.stdout),json.loads(explicit.stdout))

    def test_shorts_learning_packet_meets_the_template_short_contract(self):
        topic = "\u526a\u7247" * 40
        request = {"format":"shorts","domain":"general","topic":topic,"duration":15,
                   "beats":[{"id":"hook","role":"first_frame","energy":0.8,"subject":"hook"},
                             {"id":"answer","role":"payoff","energy":0.5,"subject":"answer"}]}
        args = [sys.executable,"-B","-X","utf8",str(SKILL / "editkin_design_bridge.py"),"--request-json",json.dumps(request),
                "--review-policy-json",json.dumps(AGENT)]
        command = subprocess.run(args,capture_output=True,text=True,encoding="utf-8",timeout=30,
                                 creationflags=getattr(subprocess,"CREATE_NO_WINDOW",0))
        self.assertEqual(command.returncode,0,command.stderr)
        learning = json.loads(command.stdout)["context"]["learning"]
        assert_public_learning(self,learning,AGENT)
        self.assertEqual(learning["route"],{"mode":"build","format":"shorts","domain":"general","topic":topic[:64]})

    def test_empty_agent_authorization_is_rejected(self):
        command = self.invoke({"mode":"agent_reference_comparison","authorization":" \n "})
        self.assertNotEqual(command.returncode,0)
        self.assertEqual(command.stdout,"")
        self.assertIn("explicit creator authorization",command.stderr)

    def test_public_source_copier_rejects_old_compiler_without_policy_contract(self):
        current = (SKILL / "editkin_design_bridge.py").read_text(encoding="utf-8")
        _assert_public_design_bridge_contract(current)
        for old in (current.replace("--review-policy-json","--retired-policy"),
                    current.replace('"reviewPolicySha256": policy_sha,','"retiredPolicySha": policy_sha,'),
                    current.replace('    "review_policy.py",\n',"")):
            with self.subTest(old_surface=old[-60:]), self.assertRaisesRegex(ValueError,"policy envelope contract"):
                _assert_public_design_bridge_contract(old)

    def test_actual_regenerator_keeps_original_public_compiler_and_neutral_runtime(self):
        with tempfile.TemporaryDirectory(prefix="public-design-regeneration-") as temporary:
            destination = Path(temporary)
            copied = _copy_public_owned(ROOT,destination)
            self.assertEqual(copied,list(PUBLIC_OWNED_PATHS))
            bridge = destination / "codex-skill/video-autopilot/editkin_design_bridge.py"
            expected = (SKILL / "editkin_design_bridge.py").read_text(encoding="utf-8-sig").replace("\r\n","\n").replace("\r","\n")
            self.assertEqual(bridge.read_bytes(),expected.encode("utf-8"))
            # The owned copier only generates owned source; normal workflow copies provide these two files.
            for relative in ("review_policy.py","workflow_contract.json","SKILL.md","references/design-reference-dna-v6.md","references/caption-art-direction.md"):
                target = bridge.parent / relative
                target.parent.mkdir(parents=True,exist_ok=True)
                shutil.copyfile(SKILL / relative,target)
            command = self.invoke(AGENT,bridge.parent)
            self.assertEqual(command.returncode,0,command.stderr)
            brief = json.loads(command.stdout)
            self.assert_bound(brief,AGENT,"agent")
            original = self.invoke(AGENT)
            self.assertEqual(original.returncode,0,original.stderr)
            self.assertEqual(brief["recipes"],json.loads(original.stdout)["recipes"])
            expected_sources = [{"path":row["path"],"sha256":hashlib.sha256((bridge.parent / row["path"]).read_bytes()).hexdigest()}
                                for row in brief["sources"]]
            self.assertEqual(brief["sources"],expected_sources)

    def test_policy_dependency_byte_change_invalidates_public_source_identity(self):
        with tempfile.TemporaryDirectory(prefix="public-design-dependency-") as temporary:
            skill = Path(temporary) / "video-autopilot"
            shutil.copytree(SKILL,skill,ignore=shutil.ignore_patterns("__pycache__"))
            before = self.invoke(AGENT,skill)
            self.assertEqual(before.returncode,0,before.stderr)
            dependency = skill / "review_policy.py"
            dependency.write_bytes(dependency.read_bytes()+b"\n# Synthetic source identity mutation only.\n")
            after = self.invoke(AGENT,skill)
            self.assertEqual(after.returncode,0,after.stderr)
            a,b = json.loads(before.stdout),json.loads(after.stdout)
            self.assertNotEqual(a["sourceSha256"],b["sourceSha256"])
            self.assertEqual(a["reviewPolicySha256"],b["reviewPolicySha256"])
            self.assertEqual(a["recipes"],b["recipes"])


class PublicCreatorPolicyLoaderTests(unittest.TestCase):
    def module(self,path):
        spec = importlib.util.spec_from_file_location("public_loader_fixture",path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def modules(self):
        return [self.module(ROOT / "src/review_policy.py"),self.module(SKILL / "review_policy.py")]

    def test_both_actual_public_loaders_reject_null_non_files_and_oversize(self):
        with tempfile.TemporaryDirectory(prefix="public-loader-controls-") as temporary:
            workspace = Path(temporary)
            path = workspace / ".autopilot/creator-review-policy.json"
            path.parent.mkdir()
            for module in self.modules():
                with self.subTest(module=module.__file__):
                    self.assertEqual(module.load_creator_review_policy(workspace),{"mode":"human"})
                    for payload in (b"null",b"[]",b"{",b" "*8193):
                        path.write_bytes(payload)
                        with self.assertRaises(ValueError):
                            module.load_creator_review_policy(workspace)
                    path.unlink()
                    path.mkdir()
                    with self.assertRaisesRegex(ValueError,"regular local"):
                        module.load_creator_review_policy(workspace)
                    path.rmdir()

    def test_both_actual_public_loaders_read_authorized_and_human_policy(self):
        with tempfile.TemporaryDirectory(prefix="public-loader-positive-") as temporary:
            workspace = Path(temporary)
            path = workspace / ".autopilot/creator-review-policy.json"
            path.parent.mkdir()
            for module in self.modules():
                for policy in (AGENT,{"mode":"human"}):
                    path.write_text(json.dumps(policy),encoding="utf-8")
                    self.assertEqual(module.load_creator_review_policy(workspace),policy)
                payload = b'{"mode":"human"}'
                path.write_bytes(payload+b" "*(8192-len(payload)))
                self.assertEqual(module.load_creator_review_policy(workspace),{"mode":"human"})

    def test_real_public_directory_junction_or_symlink_is_rejected(self):
        with tempfile.TemporaryDirectory(prefix="public-loader-alias-") as temporary:
            fixture = Path(temporary)
            workspace = fixture / "workspace"
            workspace.mkdir()
            target = fixture / "outside-authority"
            target.mkdir()
            (target / "creator-review-policy.json").write_text(json.dumps(AGENT),encoding="utf-8")
            alias = workspace / ".autopilot"
            if os.name == "nt":
                command = subprocess.run(["cmd.exe","/d","/c","mklink","/J",str(alias),str(target)],capture_output=True,
                                         timeout=10,creationflags=getattr(subprocess,"CREATE_NO_WINDOW",0))
                self.assertEqual(command.returncode,0,command.stderr)
            else:
                alias.symlink_to(target,target_is_directory=True)
            for module in self.modules():
                with self.assertRaisesRegex(ValueError,"links or junctions"):
                    module.load_creator_review_policy(workspace)

    def test_actual_neutral_generator_preserves_both_policy_dependency_outputs(self):
        with tempfile.TemporaryDirectory(prefix="public-loader-generation-") as temporary:
            fixture = Path(temporary)
            source = ROOT / "src/review_policy.py"
            for relative in ("src/review_policy.py","codex-skill/video-autopilot/review_policy.py"):
                destination = fixture / relative
                _copy_text(source,destination,relative)
                expected = source.read_text(encoding="utf-8-sig").replace("\r\n","\n").replace("\r","\n")
                self.assertEqual(destination.read_bytes(),expected.encode("utf-8"))
                module = self.module(destination)
                workspace = fixture / "workspace"
                path = workspace / ".autopilot/creator-review-policy.json"
                path.parent.mkdir(parents=True,exist_ok=True)
                path.write_bytes(b"null")
                with self.assertRaisesRegex(ValueError,"JSON object"):
                    module.load_creator_review_policy(workspace)


if __name__ == "__main__":
    unittest.main()
