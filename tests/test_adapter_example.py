"""Run the contributor example against the real daemon, without agent software."""

from concurrent.futures import ThreadPoolExecutor
import io
from pathlib import Path
import runpy
from unittest.mock import Mock, patch

from pad_lattice.events import AgentIdentity, ControlAction
from pad_lattice.protocol import ActionEvent, ProtocolError
import test_runtime_integration as runtime


run_adapter = runpy.run_path(
    str(Path(__file__).resolve().parents[1] / "examples" / "agent_adapter.py")
)["run_adapter"]


class AdapterExampleTest(runtime.RuntimeHarness):
    def start_example(self, work):
        executor = self.resources.enter_context(ThreadPoolExecutor(max_workers=1))
        return executor.submit(
            run_adapter, self.client, AgentIdentity("example", "test-example"), work,
            timeout=runtime.TIMEOUT, outcome_hold=0, output=io.StringIO(),
        )

    def test_approval_runs_work_once_and_cleans_up_the_session(self):
        browser, _ = self.browser()
        self.view(browser)
        work = Mock()
        result = self.start_example(work)
        view = self.view(browser, lambda v: "approve" in v["available_actions"])
        self.press(browser, view)
        self.press(browser, view)
        self.assertEqual(result.result(timeout=runtime.TIMEOUT), 0)
        work.assert_called_once_with()
        self.view(browser, lambda v: not v["sessions"])
        self.assertEqual(self.client.status()["sessions"], [])

    def test_rejection_does_not_run_work_and_removes_controls(self):
        browser, _ = self.browser()
        self.view(browser)
        work = Mock()
        result = self.start_example(work)
        view = self.view(browser, lambda v: "reject" in v["available_actions"])
        self.press(browser, view, "reject")
        self.assertEqual(result.result(timeout=runtime.TIMEOUT), 2)
        work.assert_not_called()
        self.view(browser, lambda v: not v["sessions"] and not v["available_actions"])

    def test_timeout_is_not_permission_to_run(self):
        work = Mock()
        result = run_adapter(
            self.client, AgentIdentity("example", "timed-out"), work,
            timeout=0.1, outcome_hold=0, output=io.StringIO(),
        )
        self.assertEqual(result, 2)
        work.assert_not_called()
        self.assertEqual(self.client.status()["sessions"], [])

    def test_work_failure_does_not_leave_a_session_or_controls(self):
        browser, _ = self.browser()
        self.view(browser)
        result = self.start_example(Mock(side_effect=RuntimeError("sample work failed")))
        view = self.view(browser, lambda v: "approve" in v["available_actions"])
        self.press(browser, view)
        with self.assertRaisesRegex(RuntimeError, "sample work failed"):
            result.result(timeout=runtime.TIMEOUT)
        self.view(browser, lambda v: not v["sessions"])

    def test_work_timeout_is_not_mistaken_for_an_unanswered_approval(self):
        browser, _ = self.browser()
        self.view(browser)
        result = self.start_example(Mock(side_effect=TimeoutError("sample work timed out")))
        view = self.view(browser, lambda v: "approve" in v["available_actions"])
        self.press(browser, view)
        with self.assertRaisesRegex(TimeoutError, "sample work timed out"):
            result.result(timeout=runtime.TIMEOUT)
        self.view(browser, lambda v: not v["sessions"])

    def test_unrelated_decision_never_runs_work(self):
        work = Mock()
        wrong = ActionEvent(AgentIdentity("example", "another-agent"), ControlAction.APPROVE, "another-request")
        with patch("pad_lattice.client.ActionSubscription.receive", return_value=wrong):
            with self.assertRaisesRegex(ProtocolError, "does not match"):
                run_adapter(self.client, AgentIdentity("example", "test-example"), work,
                            timeout=runtime.TIMEOUT, outcome_hold=0, output=io.StringIO())
        work.assert_not_called()
        self.assertEqual(self.client.status()["sessions"], [])
