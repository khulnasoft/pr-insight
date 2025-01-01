import pytest
from pr_insight.algo.utils import parse_code_suggestion


class TestParseCodeSuggestion:
    def test_empty_dict(self):
        """Test that function returns empty string when input is an empty dictionary"""
        input_data = {}
        expected_output = "\n"
        assert parse_code_suggestion(input_data) == expected_output

    def test_non_string_before_or_after(self):
        """Test that function handles non-string values in 'before' or 'after' keys"""
        input_data = {
            "Code example": {
                "Before": 123,
                "After": ["a", "b", "c"]
            }
        }
        expected_output = (
            "  - **Code example:**\n"
            "    - **Before:**\n"
            "        ```\n"
            "        123\n"
            "        ```\n"
            "    - **After:**\n"
            "        ```\n"
            "        ['a', 'b', 'c']\n"
            "        ```\n\n"
        )
        assert parse_code_suggestion(input_data) == expected_output

    def test_no_code_example_key(self):
        """Test that function handles input without 'code example' key"""
        code_suggestions = {
            'suggestion': 'Suggestion 1',
            'description': 'Description 1', 
            'before': 'Before 1',
            'after': 'After 1'
        }
        expected_output = (
            '   **suggestion:** Suggestion 1     \n'
            '   **description:** Description 1     \n'
            '   **before:** Before 1     \n'
            '   **after:** After 1     \n\n'
        )
        assert parse_code_suggestion(code_suggestions) == expected_output

    def test_with_code_example_key(self):
        """Test that function handles input with 'code example' key"""
        code_suggestions = {
            'suggestion': 'Suggestion 2',
            'description': 'Description 2',
            'code example': {
                'before': 'Before 2',
                'after': 'After 2'
            }
        }
        expected_output = (
            '   **suggestion:** Suggestion 2     \n'
            '   **description:** Description 2     \n'
            '  - **code example:**\n'
            '    - **before:**\n'
            '        ```\n'
            '        Before 2\n'
            '        ```\n'
            '    - **after:**\n'
            '        ```\n'
            '        After 2\n'
            '        ```\n\n'
        )
        assert parse_code_suggestion(code_suggestions) == expected_output
