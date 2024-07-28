from devpi_jenkins.main import render_string
import os
import pytest
import shutil
import tarfile


bootstrapindex = "http://localhost:3141/root/dev/+simple/"


@pytest.fixture(scope="session")
def bootstrapdict():
    source = render_string(
        "devpibootstrap.py",
        INDEXURL="http://localhost:3141/root/dev",
        VIRTUALENVTARURL="http://localhost:3141/root/pypi/virtualenv-1.10.tar.gz",
        DEVPI_INSTALL_INDEX="http://localhost:3141/root/dev",
        TESTSPEC="pytest")
    d = {}
    exec(compile(source, "<from bootstrapdict>", "exec"), d)
    return d


@pytest.fixture(scope="session")
def url_of_liveserver(request):
    import random
    import subprocess
    port = random.randint(2001, 64000)
    clientdir = request.config._tmpdirhandler.mktemp("liveserver")
    subprocess.check_call(["devpi-server", "--serverdir", str(clientdir),
                           "--port", str(port), "--start"])

    def stop():
        subprocess.check_call(["devpi-server", "--serverdir", str(clientdir),
                               "--stop"])

    request.addfinalizer(stop)
    return "http://localhost:%s" % port


@pytest.fixture
def virtualenv_tar(tmpdir):
    base = tmpdir.mkdir("virtualenv_build")
    script = base.ensure("virtualenv-1.10", "virtualenv.py")
    script.write("#")
    tarpath = base.join("virtualenv-1.10.tar.gz")
    tar = tarfile.open(tarpath.strpath, "w:gz")
    tar.add(str(script), script.relto(base))
    tar.close()
    print("created %s" % tarpath.strpath)
    return tarpath.strpath


def test_bootstrapdict_create(bootstrapdict):
    assert "Devpi" in bootstrapdict


def test_get_virtualenv(tmpdir, bootstrapdict, virtualenv_tar, monkeypatch):
    monkeypatch.chdir(tmpdir)
    get_virtualenv = bootstrapdict["get_virtualenv"]
    vurl = "http://localhost:3141/root/pypi/virtualenv-1.10.tar.gz"

    def urlretrieve(url, localpath):
        assert url == vurl
        shutil.copy(virtualenv_tar, localpath)

    monkeypatch.setitem(bootstrapdict, "urlretrieve", urlretrieve)
    virtualenv_script = get_virtualenv(vurl)
    assert os.path.exists(virtualenv_script)
    # check that a second attempt won't hit the web
    monkeypatch.setitem(bootstrapdict, "wget", None)
    virtualenv_script = get_virtualenv(vurl)
    assert os.path.exists(virtualenv_script)


@pytest.mark.xfail(reason="cannot provide current devpi-server "
                   "safely in an index")
def test_main(request, url_of_liveserver, mapp, tmpdir, monkeypatch):
    # not a very good test as it requires going to pypi.python.org
    mapp.login_root()
    mapp.create_index("root/dev")
    tmpdir.chdir()
    source = render_string(
        "devpibootstrap.py",
        INDEXURL=url_of_liveserver + "/root/dev",
        VIRTUALENVTARURL=("https://pypi.python.org/packages/source/"
                          "v/virtualenv/virtualenv-1.10.tar.gz"),
        DEVPI_INSTALL_INDEX=url_of_liveserver + "/root/dev/+simple/",
        TESTSPEC="py")
    d = {}
    exec(compile(source, "<from test_main>", "exec"), d)
    l = []

    def record(*args, **kwargs):
        l.append(args)

    monkeypatch.setattr(d["Devpi"], "run", record)
    d["main"]()
    assert len(l) == 2
    assert "use" in l[0][1]
    assert "test" in l[1][1]
