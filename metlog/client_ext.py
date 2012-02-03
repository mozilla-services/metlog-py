def log_cef(self, name, severity, environ, config, username='none',
            signature=None, **kw):
    """Creates a CEF record, and emit it in syslog or another file.

    Args:
        - name: name to log
        - severity: integer from 0 to 10
        - environ: the WSGI environ object
        - config: configuration dict
        - signature: CEF signature code - defaults to name value
        - username: user name - defaults to 'none'
        - extra keywords: extra keys used in the CEF extension
    """
    from cef import _get_fields, _format_msg, _filter_params
    config = _filter_params('cef', config)
    fields = _get_fields(name, severity, environ, config, username=username,
                        signature=signature, **kw)
    msg = _format_msg(fields, kw)

    self.metlog(type='cef', payload=msg)

    # Return the formatted message
    return msg
