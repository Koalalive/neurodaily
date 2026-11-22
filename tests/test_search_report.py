import re
import tempfile
import unittest
from unittest import mock

from neurodaily import ai_summary
from neurodaily.demo import build_result
from neurodaily.render import render_html


class SearchReportTests(unittest.TestCase):
    def test_explains_item_match_and_source_coverage(self):
        result = build_result()
        result.config.search = {"sort": "relevance"}
        item = result.sections["papers"][0]
        item.extra.update(
            search_match="unknown",
            matched_rules=['TI="working memory"'],
            missing_fields=["AB"],
            provenance=[
                {"source": "PubMed", "url": "https://example.com/pubmed"},
                {"source": "期刊 RSS", "url": "javascript:alert(1)"},
            ],
            related_versions=[
                {"title": "Published article", "kind": "published", "url": "https://example.com/published"},
            ],
        )
        result.health = [
            {"source": "pubmed", "status": "empty", "ok": True, "count": 0,
             "candidate_count": 4, "fetched": 4, "ms": 12, "coverage": "sampled",
             "queries": ['TI="working memory"', "AB=<b>EEG</b>"], "truncated": True,
             "unknown": 2, "lookback_days": 7},
            {"source": "arxiv", "status": "timeout", "ok": False, "count": 0,
             "ms": 60, "error": "request deadline exceeded"},
        ]

        html = render_html(result)
        for content in (
            "排序 · 相关性", "待确认", "命中依据", "无法判断的字段", "AB",
            "合并来源", "相关版本", "正式发表 · Published article", "无命中", "超时", "样本范围内的结果",
            "已到达抓取上限", "request deadline exceeded",
            "2 条因字段不足待确认", "请求回溯 · 7 天",
            '<a href="#source-health">📡 来源状态</a>',
            'href="https://example.com/pubmed"', 'href="https://example.com/published"',
        ):
            self.assertIn(content, html)
        self.assertNotIn('href="javascript:', html)
        self.assertNotIn("AB=&lt;b&gt;EEG&lt;/b&gt;", html)

    def test_report_rejects_summary_refs_outside_actual_results(self):
        result = build_result()
        result.ai_summary = "证据（[错误引用](R1)）。"
        result.ai_summary_refs = {"R1": {"url": "https://example.com/not-a-result"}}
        html = render_html(result)
        self.assertIn("错误引用", html)
        self.assertNotIn('href="https://example.com/not-a-result"', html)


class CitationGroundingTests(unittest.TestCase):
    def test_only_explicit_available_ids_become_links(self):
        refs = {
            "R1": {"title": "Evidence one", "journal": "Nature", "url": "https://example.com/1"},
            "R2": {"title": "Evidence two", "journal": "eLife", "url": "https://example.com/2"},
        }
        summary = ai_summary._ground_summary(
            "另一组研究（Nature）无编号。有效结果（R1、R2、R99、R1）。"
            "不支持的条目[R99]。任意链接[资料](https://evil.example)和 https://bare.example。",
            refs,
        )
        self.assertEqual(re.findall(r"\]\((R\d+)\)", summary), ["R1", "R2"])
        self.assertIn("另一组研究Nature无编号", summary)
        self.assertNotIn("evil.example", summary)
        self.assertNotIn("bare.example", summary)
        self.assertNotIn("R99", summary)
        self.assertEqual(ai_summary._ground_summary(summary, refs), summary)

    def test_input_cap_and_unknown_match_change_reference_set(self):
        result = build_result()
        result.on_this_day = []
        keep, omit = result.sections["papers"][:2]
        result.sections = {"papers": [keep]}
        first_prompt, _ = ai_summary.build_context(result, ai_summary.DEFAULT_CFG)
        result.sections["papers"].append(omit)

        prompt, refs = ai_summary.build_context(
            result, {**ai_summary.DEFAULT_CFG, "max_input_chars": len(first_prompt)}
        )
        self.assertEqual(set(refs), {"R1"})
        self.assertIn("R1. " + keep.title, prompt)
        self.assertNotIn(omit.title, prompt)

        keep.extra["search_match"] = "unknown"
        prompt, refs = ai_summary.build_context(result, ai_summary.DEFAULT_CFG)
        self.assertEqual(set(refs), {"R1"})
        self.assertEqual(refs["R1"]["title"], omit.title)
        self.assertNotIn(keep.title, prompt)

    def test_generate_uses_single_model_pass_and_invalidates_on_evidence_change(self):
        result = build_result()
        with tempfile.TemporaryDirectory() as directory:
            result.config.output["dir"] = directory
            with mock.patch.object(ai_summary, "_call_llm", return_value="事实（R1）。") as call, \
                 mock.patch.object(ai_summary.httpx, "post") as direct_post:
                result1 = ai_summary.generate(result, ai_summary.DEFAULT_CFG, api_key_override="test")
                result2 = ai_summary.generate(result, ai_summary.DEFAULT_CFG, api_key_override="test")
                self.assertEqual(result1, result2)
                self.assertEqual(call.call_count, 1)
                result.sections["papers"][0].summary = "New evidence for the same URL"
                ai_summary.generate(result, ai_summary.DEFAULT_CFG, api_key_override="test")
                self.assertEqual(call.call_count, 2)
                direct_post.assert_not_called()


if __name__ == "__main__":
    unittest.main()
