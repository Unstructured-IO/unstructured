from setup_utils import load_requirements


def test_load_requirements():
    file = "./files/example.in"
    reqs = load_requirements(file_list=[file])
    desired_deps = ["torch", "httpx", "requests", "sphinx<4.3.2", "pandas"]
    assert len(reqs) == len(desired_deps)
    assert sorted(reqs) == sorted(desired_deps)
