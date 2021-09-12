import copy
from contextlib import closing

from pathlib import Path
from typing import Dict
import requests
from requests import Session
from resumable import path, DownloadCheck, is_download_complete, get_resource_size, DownloadError, starting_range, \
    write_response


def urlretrieve(url: str, filename: path, session: Session=None, reporthook=None, method='GET',
                sha256sum=None, filesize=None, headers=None,
                **kwargs) -> Dict[str, str]:
    D = DownloadCheck  # type: Any
    filename = Path(filename)
    if is_download_complete(filename, sha256sum, filesize) != D.completed:
        size = filename.stat().st_size if filename.exists() else None
        _headers = copy.deepcopy(headers) or {}
        _headers.update({'Range': 'bytes=%s-' % size} if size is not None else {})
        request_func = requests.request if session is None else session.request
        head_func = requests.head if session is None else session.head
        with closing(request_func(method, url, stream=True, headers=_headers, **kwargs)) as resp:
            remote_size = get_resource_size(resp.headers)
            already_completed = resp.status_code == 416
            if not already_completed:
                try:
                    resp.raise_for_status()
                except requests.exceptions.HTTPError as e:
                    __headers = copy.deepcopy(_headers)
                    if 'Range' in __headers:
                        del __headers['Range']
                    try:
                        with closing(head_func(url, headers=__headers, **kwargs)) as hresp:
                            remote_size = get_resource_size(hresp.headers)
                            if remote_size == size:
                                return hresp.headers
                    except Exception as e:
                        raise DownloadError(e)
                    raise DownloadError(e)
                write_response(resp, filename, reporthook, size, remote_size)
                check = is_download_complete(filename, sha256sum, filesize)
                if check not in (D.completed, D.partial):
                    raise DownloadError(check)
            return resp.headers

