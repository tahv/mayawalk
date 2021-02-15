import setuptools
import ast


def get_version(filepath):
    with open(filepath, "r") as f:
        root = ast.parse(f.read())
    version = None
    for statement in root.body:
        if isinstance(statement, ast.Assign):
            for target in statement.targets:
                if isinstance(target, ast.Name) and target.id == "__version__":
                    return ast.literal_eval(statement.value)
    assert version, "Could not determine version"
    return version


with open("README.md", "r") as f:
    long_description = f.read()


setuptools.setup(
    name="mayawalk",
    version=get_version("mayawalk.py"),
    description="Collection of traversal algorithms for Autodesk Maya",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Thibaud Gambier",
    license="MIT",
    url="https://github.com/tahv/mayawalk",
    py_modules=["mayawalk"],
)
