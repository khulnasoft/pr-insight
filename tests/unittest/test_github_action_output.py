import os
import json
import pytest
from pr_insight.algo.utils import get_settings, github_action_output


class TestGitHubOutput:
    @pytest.fixture
    def output_file(self, tmp_path):
        """Fixture to create and return output file path"""
        return str(tmp_path / 'output')

    @pytest.fixture
    def test_data(self):
        """Fixture to provide test data"""
        return {
            'key1': {
                'value1': 1,
                'value2': 2
            }
        }

    def test_github_action_output_enabled(self, monkeypatch, output_file, test_data):
        """Test that output is written when GitHub Actions output is enabled"""
        get_settings().set('GITHUB_ACTION_CONFIG.ENABLE_OUTPUT', True)
        monkeypatch.setenv('GITHUB_OUTPUT', output_file)
        key_name = 'key1'
        
        github_action_output(test_data, key_name)
        
        with open(output_file, 'r') as f:
            env_value = f.read()
        
        actual_key, actual_data_str = env_value.split('=')
        actual_data = json.loads(actual_data_str)
        
        assert actual_key == key_name
        assert actual_data == test_data[key_name]
    
    def test_github_action_output_disabled(self, monkeypatch, output_file, test_data):
        """Test that no output is written when GitHub Actions output is disabled"""
        get_settings().set('GITHUB_ACTION_CONFIG.ENABLE_OUTPUT', False)
        monkeypatch.setenv('GITHUB_OUTPUT', output_file)
        
        github_action_output(test_data, 'key1')
        
        assert not os.path.exists(output_file)

    def test_github_action_output_notset(self, monkeypatch, output_file, test_data):
        """Test that no output is written when GitHub Actions config is not set"""
        monkeypatch.setenv('GITHUB_OUTPUT', output_file)
        
        github_action_output(test_data, 'key1')
        
        assert not os.path.exists(output_file)
    
    @pytest.mark.parametrize('invalid_data', [
        None,
        {},
        {'key1': None},
        {'key1': ''},
    ])
    def test_github_action_output_error_cases(self, monkeypatch, output_file, invalid_data):
        """Test that no output is written for various invalid input data"""
        get_settings().set('GITHUB_ACTION_CONFIG.ENABLE_OUTPUT', True)
        monkeypatch.setenv('GITHUB_OUTPUT', output_file)
        
        github_action_output(invalid_data, 'key1')
        
        assert not os.path.exists(output_file)