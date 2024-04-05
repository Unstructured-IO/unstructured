from setup_utils import load_requirements


def test_load_requirments():
    file = "./files/example.in"
    reqs = load_requirements(file_list=[file])
    assert len(reqs) == 4
    desired_deps = ["torch", "httpx", "requests", "pandas"]
    assert reqs == desired_deps
