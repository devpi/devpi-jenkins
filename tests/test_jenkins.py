import pytest


@pytest.fixture
def xom(makexom):
    from devpi_jenkins import main
    xom = makexom(plugins=[(main, None)])
    return xom


@pytest.mark.notransaction
def test_create_index_with_jenkinsurl(mapp):
    url = "http://localhost:8080/"
    mapp.login_root()
    mapp.create_index("root/test3")
    mapp.use("root/test3")
    mapp.set_indexconfig_option("uploadtrigger_jenkins", url)
    data = mapp.getjson("/root/test3")
    assert data["result"]["uploadtrigger_jenkins"] == url


@pytest.mark.notransaction
def test_upload_with_jenkins(mapp, reqmock):
    from io import BytesIO
    import cgi
    import json
    mapp.create_and_use()
    mapp.set_indexconfig_option("uploadtrigger_jenkins", "http://x.com/{pkgname}/{pkgversion}")
    rec = reqmock.mockresponse(code=200, url=None)
    mapp.upload_file_pypi("pkg1-2.6.tgz", b"123", "pkg1", "2.6", code=200)
    assert len(rec.requests) == 1
    req = rec.requests[0]
    assert req.url == "http://x.com/pkg1/2.6"
    fs = cgi.FieldStorage(
        BytesIO(req.body), req.headers, environ=dict(REQUEST_METHOD='POST'))
    assert fs.getfirst("Submit") == "Build"
    assert json.loads(fs.getfirst("json")) == {
        "parameter": {"file": "file0", "name": "jobscript.py"}}
    assert fs.getfirst("name") == "jobscript.py"
    script = fs.getfirst("file0")
    assert script.startswith(b'#!/')
    assert b'indexurl = "http://localhost/user1/dev"' in script
    assert b'virtualenvtar_url = "http://localhost/root/pypi/+f/f61/cdd983d2c4e6a/virtualenv-1.11.6.tar.gz"' in script
    assert b'devpi_install_index = "http://localhost/user1/dev/+simple/"' in script
    assert b'testspec = "pkg1==2.6"' in script
