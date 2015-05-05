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
    mapp.create_and_use()
    mapp.set_indexconfig_option("uploadtrigger_jenkins", "http://x.com/{pkgname}/{pkgversion}")
    rec = reqmock.mockresponse(code=200, url=None)
    mapp.upload_file_pypi("pkg1-2.6.tgz", b"123", "pkg1", "2.6", code=200)
    assert len(rec.requests) == 1
    assert rec.requests[0].url == "http://x.com/pkg1/2.6"
    # XXX properly decode form
    # assert args[1]["data"]["Submit"] == "Build"
