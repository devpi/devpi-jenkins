from __future__ import unicode_literals
from devpi_common.request import new_requests_session
from devpi_jenkins import __version__
import json
import py


def render_string(confname, format=None, **kw):
    template = confname + ".template"
    from pkg_resources import resource_string
    templatestring = resource_string("devpi_jenkins", template)
    if not py.builtin._istext(templatestring):
        templatestring = py.builtin._totext(templatestring, "utf-8")

    kw = dict((x[0], str(x[1])) for x in kw.items())
    if format is None:
        result = templatestring.format(**kw)
    else:
        result = templatestring % kw
    return result


def devpiserver_indexconfig_defaults():
    return {"uploadtrigger_jenkins": None}


def devpiserver_on_upload_sync(log, application_url, stage, projectname, version):
    jenkinsurl = stage.ixconfig.get("uploadtrigger_jenkins")
    if not jenkinsurl:
        return
    jenkinsurl = jenkinsurl.format(pkgname=projectname, pkgversion=version)

    source = render_string(
        "devpibootstrap.py",
        INDEXURL=application_url + "/" + stage.name,
        VIRTUALENVTARURL=(
            application_url +
            "/root/pypi/+f/f61/cdd983d2c4e6a/"
            "virtualenv-1.11.6.tar.gz"),
        TESTSPEC='%s==%s' % (projectname, version),
        DEVPI_INSTALL_INDEX=application_url + "/" + stage.name + "/+simple/")
    inputfile = py.io.BytesIO(source.encode("ascii"))
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
                           projectname, jenkinsurl)

    if 200 <= r.status_code < 300:
        log.info("successfully triggered jenkins: %s", jenkinsurl)
    else:
        log.error("%s: failed to trigger jenkins at %s", r.status_code,
                  jenkinsurl)
        log.debug(r.content)
        raise RuntimeError("%s: failed to trigger jenkins at %s",
                           projectname, jenkinsurl)
