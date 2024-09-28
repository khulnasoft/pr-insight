# Generated by KhulnaSoft
from pr_insight.algo.utils import PRReviewHeader, convert_to_markdown_v2
from pr_insight.tools.pr_description import insert_br_after_x_chars

"""
Code Analysis

Objective:
The objective of the 'convert_to_markdown' function is to convert a dictionary of data into a markdown-formatted text. 
The function takes in a dictionary as input and recursively iterates through its keys and values to generate the 
markdown text.

Inputs:
- A dictionary of data containing information about a pull request.

Flow:
- Initialize an empty string variable 'markdown_text'.
- Create a dictionary 'emojis' containing emojis for each key in the input dictionary.
- Iterate through the input dictionary:
  - If the value is empty, continue to the next iteration.
  - If the value is a dictionary, recursively call the 'convert_to_markdown' function with the value as input and 
  append the returned markdown text to 'markdown_text'.
  - If the value is a list:
    - If the key is 'code suggestions', add an additional line break to 'markdown_text'.
    - Get the corresponding emoji for the key from the 'emojis' dictionary. If no emoji is found, use a dash.
    - Append the emoji and key to 'markdown_text'.
    - Iterate through the items in the list:
      - If the item is a dictionary and the key is 'code suggestions', call the 'parse_code_suggestion' function with 
      the item as input and append the returned markdown text to 'markdown_text'.
      - If the item is not empty, append it to 'markdown_text'.
  - If the value is not 'n/a', get the corresponding emoji for the key from the 'emojis' dictionary. If no emoji is 
  found, use a dash. Append the emoji, key, and value to 'markdown_text'.
- Return 'markdown_text'.

Outputs:
- A markdown-formatted string containing the information from the input dictionary.

Additional aspects:
- The function uses recursion to handle nested dictionaries.
- The 'parse_code_suggestion' function is called for items in the 'code suggestions' list.
- The function uses emojis to add visual cues to the markdown text.
"""


class TestConvertToMarkdown:
    # Tests that the function works correctly with a simple dictionary input
    def test_simple_dictionary_input(self):
        input_data = {'review': {
            'estimated_effort_to_review_[1-5]': '1, because the changes are minimal and straightforward, focusing on a single functionality addition.\n',
            'relevant_tests': 'No\n', 'possible_issues': 'No\n', 'security_concerns': 'No\n'}, 'code_feedback': [
            {'relevant_file': '``pr_insight/git_providers/git_provider.py\n``', 'language': 'python\n',
             'suggestion': "Consider raising an exception or logging a warning when 'pr_url' attribute is not found. This can help in debugging issues related to the absence of 'pr_url' in instances where it's expected. [important]\n",
             'relevant_line': '[return ""](https://github.com/Khulnasoft/pr-insight-pro/pull/102/files#diff-52d45f12b836f77ed1aef86e972e65404634ea4e2a6083fb71a9b0f9bb9e062fR199)'}]}

        expected_output = (
            f'{PRReviewHeader.REGULAR.value} 🔍\n\n'
            '<table>\n'
            '<tr><td>⏱️&nbsp;<strong>Estimated effort to review</strong>: 1 🔵⚪⚪⚪⚪</td></tr>\n'
            '<tr><td>🧪&nbsp;<strong>No relevant tests</strong></td></tr>\n'
            '<tr><td>⚡&nbsp;<strong>Possible issues</strong>: No\n</td></tr>\n'
            '<tr><td>🔒&nbsp;<strong>No security concerns identified</strong></td></tr>\n'
            '</table>\n\n\n'
            '<details><summary> <strong>Code feedback:</strong></summary>\n\n'
            '<hr><table><tr><td>relevant file</td><td>pr_insight/git_providers/git_provider.py\n</td></tr>'
            '<tr><td>suggestion &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;</td><td>\n\n'
            '<strong>\n\nConsider raising an exception or logging a warning when \'pr_url\' attribute is not found. '
            'This can help in debugging issues related to the absence of \'pr_url\' in instances where it\'s expected. '
            '[important]\n\n</strong>\n</td></tr>'
            '<tr><td>relevant line</td><td><a href=\'https://github.com/Khulnasoft/pr-insight-pro/pull/102/files#'
            'diff-52d45f12b836f77ed1aef86e972e65404634ea4e2a6083fb71a9b0f9bb9e062fR199\'>return ""</a></td></tr>'
            '</table><hr>\n\n</details>'
        )

        assert convert_to_markdown_v2(input_data).strip() == expected_output.strip()

    # Tests that the function works correctly with an empty dictionary input
    def test_empty_dictionary_input(self):
        input_data = {}
        expected_output = ''
        assert convert_to_markdown_v2(input_data).strip() == expected_output.strip()

    # Test dictionary with empty inner dictionaries
    def test_dictionary_with_empty_dictionaries(self):
        input_data = {'review': {}, 'code_feedback': [{}]}
        expected_output = ''
        assert convert_to_markdown_v2(input_data).strip() == expected_output.strip()


class TestBR:
    def test_br1(self):
        file_change_description = '- Imported `FilePatchInfo` and `EDIT_TYPE` from `pr_insight.algo.types` instead of `pr_insight.git_providers.git_provider`.'
        file_change_description_br = insert_br_after_x_chars(file_change_description)
        expected_output = ('<li>Imported <code>FilePatchInfo</code> and <code>EDIT_TYPE</code> from '
                           '<code>pr_insight.algo.types</code> instead <br>of '
                           '<code>pr_insight.git_providers.git_provider</code>.')
        assert file_change_description_br == expected_output

    def test_br2(self):
        file_change_description = (
            '- Created a - new -class `ColorPaletteResourcesCollection ColorPaletteResourcesCollection '
            'ColorPaletteResourcesCollection ColorPaletteResourcesCollection`')
        file_change_description_br = insert_br_after_x_chars(file_change_description)
        expected_output = ('<li>Created a - new -class <code>ColorPaletteResourcesCollection </code><br><code>'
                           'ColorPaletteResourcesCollection ColorPaletteResourcesCollection '
                           '</code><br><code>ColorPaletteResourcesCollection</code>')
        assert file_change_description_br == expected_output

    def test_br3(self):
        file_change_description = 'Created a new class `ColorPaletteResourcesCollection` which extends `AvaloniaDictionary<ThemeVariant, ColorPaletteResources>` and implements aaa'
        file_change_description_br = insert_br_after_x_chars(file_change_description)
        expected_output = ('Created a new class <code>ColorPaletteResourcesCollection</code> which '
                           'extends <br><code>AvaloniaDictionary<ThemeVariant, ColorPaletteResources>'
                           '</code> and implements <br>aaa')
        assert file_change_description_br == expected_output
