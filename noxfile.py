import nox


@nox.session(python=["3.11", "3.13"])
def tests(session):
    session.install("./tools", "pytest")
    session.run("pytest", "-q", "tests")
