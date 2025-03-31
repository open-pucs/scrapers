import pytest
from jinja2 import Environment, FileSystemLoader, select_autoescape, UndefinedError
from pathlib import Path


# Set up Jinja environment for testing
#
def raise_helper(msg):
    raise Exception(msg)


env = Environment(loader=FileSystemLoader("./prompts"), autoescape=select_autoescape())
env.globals["raise"] = raise_helper
# Test data
valid_test_data = {
    "generic_adapters_prompt.md": {"schemas": "test schema content"},
    "refactor_prompt.md": {"scraper": "test scraper content"},
    "final_recombine_prompt.md": {
        "adapters": "test adapter content",
        "scrapers": "test scraper content",
    },
    "initial_recognisance_prompt.md": {"url": "https://example.com"},
    "make_scraper_prompt.md": {
        "url": "https://example.com",
        "schema": "test schema content",
    },
}


@pytest.fixture
def template_env():
    """Fixture to provide template environment"""
    return env


def test_templates_exist():
    """Test that all required templates exist"""
    for template_name in valid_test_data.keys():
        template = env.get_template(template_name)
        assert template is not None


@pytest.mark.parametrize("template_name,valid_data", valid_test_data.items())
def test_template_with_valid_data(template_env, template_name, valid_data):
    """Test that templates work with valid data"""
    template = template_env.get_template(template_name)
    try:
        result = template.render(**valid_data)
        assert result is not None
        assert isinstance(result, str)
        assert len(result) > 0
    except Exception as e:
        pytest.fail(f"Template {template_name} failed with valid data: {e}")


@pytest.mark.parametrize("template_name,valid_data", valid_test_data.items())
def test_template_with_missing_data(template_env, template_name, valid_data):
    """Test that templates raise appropriate exceptions with missing data"""
    template = template_env.get_template(template_name)

    # Test with empty data
    with pytest.raises(Exception):
        template.render()

    # Test with partial data
    # for key in valid_data.keys():
    #     partial_data = valid_data.copy()
    #     del partial_data[key]
    #     with pytest.raises(Exception):
    #         template.render(**partial_data)


# @pytest.mark.parametrize("template_name,valid_data", valid_test_data.items())
# def test_template_with_invalid_data_types(template_env, template_name, valid_data):
#     """Test that templates handle invalid data types appropriately"""
#     template = template_env.get_template(template_name)
#
#     # Test with None values
#     invalid_data = {k: None for k in valid_data.keys()}
#     with pytest.raises(Exception):
#         template.render(**invalid_data)
#
#     # Test with wrong types
#     invalid_data = {k: 123 for k in valid_data.keys()}  # Numbers instead of strings
#     try:
#         result = template.render(**invalid_data)
#         assert result is not None  # Templates should handle type conversion
#     except Exception as e:
#         pytest.fail(f"Template {template_name} failed with type conversion: {e}")


# def test_template_content_markers():
#     """Test that templates contain expected markers/sections"""
#     markers = {
#         "generic_adapters_prompt.md": ["schemas"],
#         "refactor_prompt.md": ["scraper"],
#         "final_recombine_prompt.md": ["adapters", "scrapers"],
#         "initial_recognisance_prompt.md": ["url"],
#         "make_scraper_prompt.md": ["url", "schema"],
#     }
#
#     for template_name, expected_markers in markers.items():
#         template = env.get_template(template_name)
#         template_source = template.filename
#
#         if template_source:
#             with open(template_source, "r") as f:
#                 content = f.read()
#                 for marker in expected_markers:
#                     assert (
#                         "{{" + marker + "}}" in content
#                         or "{%" + marker + "%}" in content
#                     ), f"Template {template_name} missing marker {marker}"


if __name__ == "__main__":
    pytest.main([__file__])
