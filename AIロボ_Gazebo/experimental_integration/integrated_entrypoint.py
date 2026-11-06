#!/usr/bin/env python3
"""AIロボ experiment: ROS 2 C81 decision gates CRANE+ execution.

This is a controlled *synthetic-feature* bridge, NOT camera perception.
No Gazebo motion occurs without --execute and a verified PICK reply.
"""
import argparse
import datetime
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import uuid

CLASSES = ("paper", "cup", "wrapper", "personal")


def check_reply(reply, *, session, seq, policy_sha):
    if not isinstance(reply, dict):
        raise ValueError("INVALID_REPLY")
    if reply.get("session_id") != session or type(reply.get("seq")) is not int or reply["seq"] != seq:
        raise ValueError("STALE_OR_REPLAYED_REPLY")
    if reply.get("policy_sha256") != policy_sha:
        raise ValueError("POLICY_HASH_MISMATCH")
    label = reply.get("label")
    if label not in CLASSES:
        raise ValueError("UNKNOWN_CLASS")
    confidence = reply.get("confidence")
    if isinstance(confidence, bool) or not isinstance(confidence, (int, float)) or not 0 <= confidence <= 1:
        raise ValueError("INVALID_CONFIDENCE")
    expected = "SKIP" if label == "personal" or confidence < .75 else "PICK"
    if reply.get("safety") != expected:
        raise ValueError("INVALID_SAFETY_ACTION")
    return expected


def load_policy(path):
    spec = importlib.util.spec_from_file_location("pai_c81_ai_node", str(path))
    if spec is None or spec.loader is None:
        raise RuntimeError("POLICY_LOAD_FAILED")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def request_decision(*, features, sha, timeout, domain):
    import rclpy
    from std_msgs.msg import String
    os.environ["ROS_DOMAIN_ID"] = str(domain)
    rclpy.init()
    node = rclpy.create_node("airobo_c81_to_crane_gate")
    pub = node.create_publisher(String, "/pai_b/object_features", 10)
    messages = []
    node.create_subscription(String, "/pai_b/ai_classification", lambda m: messages.append(m.data), 10)
    session, seq = uuid.uuid4().hex, 1
    payload = {"session_id": session, "seq": seq, "features": list(map(float, features)),
               "object_id": "synthetic_known_target", "phase": "PRE_MOTION_GATE"}
    try:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            msg = String(); msg.data = json.dumps(payload, separators=(",", ":"))
            pub.publish(msg)
            rclpy.spin_once(node, timeout_sec=.2)
            while messages:
                try:
                    result = json.loads(messages.pop(0))
                    action = check_reply(result, session=session, seq=seq, policy_sha=sha)
                    return action, result
                except (ValueError, TypeError, KeyError, json.JSONDecodeError):
                    continue
        raise TimeoutError("AI_DECISION_TIMEOUT_FAIL_CLOSED")
    finally:
        node.destroy_node()
        rclpy.shutdown()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--scenario", choices=("paper", "personal"), required=True)
    p.add_argument("--policy", type=Path, required=True, help="Path to existing C81/pai_c81_ai_node.py")
    p.add_argument("--motion-dir", type=Path, default=Path(__file__).resolve().parent)
    p.add_argument("--domain", type=int, default=84)
    p.add_argument("--timeout", type=float, default=12.)
    p.add_argument("--execute", action="store_true", help="Allow real Gazebo run ONLY after PICK")
    p.add_argument("--log", type=Path, default=None)
    args = p.parse_args()
    record = {"timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
              "scenario": args.scenario, "feature_source": "SYNTHETIC_C81_PROTOTYPE",
              "execute_requested": args.execute, "motion_started": False, "status": "FAIL_CLOSED"}
    try:
        policy = load_policy(args.policy)
        i = 0 if args.scenario == "paper" else 3
        features = policy.PROTOTYPES[i].tolist()
        action, reply = request_decision(features=features, sha=policy.SHA,
                                         timeout=args.timeout, domain=args.domain)
        record.update(action=action, reply=reply)
        if action == "SKIP":
            record["status"] = "SKIPPED_NO_MOTION"
        elif args.execute:
            motion = args.motion_dir / "run.sh"
            if not motion.is_file():
                raise FileNotFoundError("MOTION_SCRIPT_NOT_FOUND")
            record["motion_started"] = True
            completed = subprocess.run(["bash", str(motion)], cwd=str(args.motion_dir), check=False)
            record["motion_exit_code"] = completed.returncode
            record["status"] = "MOTION_PROCESS_EXITED" if completed.returncode == 0 else "MOTION_FAILED"
        else:
            record["status"] = "PICK_APPROVED_DRY_RUN"
    except Exception as e:
        record["error"] = str(e)
    finally:
        if args.log:
            args.log.parent.mkdir(parents=True, exist_ok=True)
            args.log.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(record, ensure_ascii=False))
    return 0 if record["status"] in ("SKIPPED_NO_MOTION", "PICK_APPROVED_DRY_RUN", "MOTION_PROCESS_EXITED") else 1


if __name__ == "__main__":
    sys.exit(main())
