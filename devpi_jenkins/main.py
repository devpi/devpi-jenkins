from devpi_common.request import new_requests_session
from devpi_jenkins import __version__
from io import BytesIO
from pluggy import HookimplMarker
import json


server_hookimpl = HookimplMarker("devpiserver")


def render_string(confname, format=None, **kw):
    template = confname + ".template"
    from importlib.resources import read_text
    templatestring = read_text("devpi_jenkins", template)

    kw = dict((x[0], str(x[1])) for x in kw.items())
    if format is None:
        result = templatestring.format(**kw)
    else:
        result = templatestring % kw
    return result


@server_hookimpl
def devpiserver_indexconfig_defaults():
    return {"uploadtrigger_jenkins": None}


@server_hookimpl
def devpiserver_on_upload_sync(log, application_url, stage, project, version):
    jenkinsurl = stage.ixconfig.get("uploadtrigger_jenkins")
    if not jenkinsurl:
        return
    jenkinsurl = jenkinsurl.format(pkgname=project, pkgversion=version)

    source = render_string(
        "devpibootstrap.py",
        INDEXURL=application_url + "/" + stage.name,
        VIRTUALENVTARURL=(
            application_url +
            "/root/pypi/+f/f61/cdd983d2c4e6a/"
            "virtualenv-1.11.6.tar.gz"),
        TESTSPEC='%s==%s' % (project, version),
        DEVPI_INSTALL_INDEX=application_url + "/" + stage.name + "/+simple/")
    inputfile = BytesIO(source.encode("ascii"))
    session = new_requests_session(agent=("devpi-jenkins", __version__))
    try:
        r = session.post(
            jenkinsurl,
            data={
                "Submit": "Build",
                "name": "jobscript.py",
                "json": json.dumps({
                    "parameter": {"name": "jobscript.py", "file": "file0"}})},
            files={"file0": ("file0", inputfile)})
    except session.Errors:
        raise RuntimeError("%s: failed to connect to jenkins at %s",
                           project, jenkinsurl)

    if 200 <= r.status_code < 300:
        log.info("successfully triggered jenkins: %s", jenkinsurl)
    else:
        log.error("%s: failed to trigger jenkins at %s", r.status_code,
                  jenkinsurl)
        log.debug(r.content)
        raise RuntimeError("%s: failed to trigger jenkins at %s",
                           project, jenkinsurl)
