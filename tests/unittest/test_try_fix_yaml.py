# Generated by KhulnaSoft
import pytest
from pr_insight.algo.utils import try_fix_yaml


class TestTryFixYaml:
    def test_valid_yaml(self):
        """Test that the function successfully parses a valid YAML string"""
        review_text = "key: value\n"
        expected_output = {"key": "value"}
        assert try_fix_yaml(review_text) == expected_output

    def test_add_relevant_line(self):
        """Test that '|-' is added to 'relevant line:' if not present"""
        review_text = "relevant line: value: 3\n"
        expected_output = {'relevant line': 'value: 3\n'}
        assert try_fix_yaml(review_text) == expected_output

    def test_extract_yaml_snippet(self):
        """Test extraction of YAML snippet from markdown code block"""
        review_text = '''\
Here is the answer in YAML format: