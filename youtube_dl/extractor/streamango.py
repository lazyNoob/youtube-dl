# coding: utf-8
from __future__ import unicode_literals

import re


from .common import InfoExtractor
from ..utils import (
    determine_ext,
    int_or_none,
    js_to_json,
)
#Executing node
import subprocess
#Only to suppress url "as string" warning
from ..compat import (
    compat_str,
)

class StreamangoIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?streamango\.com/(?:f|embed)/(?P<id>[^/?#&]+)'
    _TESTS = [{
        'url': 'https://streamango.com/f/clapasobsptpkdfe/20170315_150006_mp4',
        'md5': 'e992787515a182f55e38fc97588d802a',
        'info_dict': {
            'id': 'clapasobsptpkdfe',
            'ext': 'mp4',
            'title': '20170315_150006.mp4',
        }
    }, {
        # no og:title
        'url': 'https://streamango.com/embed/foqebrpftarclpob/asdf_asd_2_mp4',
        'info_dict': {
            'id': 'foqebrpftarclpob',
            'ext': 'mp4',
            'title': 'foqebrpftarclpob',
        },
        'params': {
            'skip_download': True,
        },
    }, {
        'url': 'https://streamango.com/embed/clapasobsptpkdfe/20170315_150006_mp4',
        'only_matching': True,
    }]

    def _decrypt_url(self, webpage, encrypted_src):
    
        regex = r"(eval\(function\(p,a,c,k,e,r\).*)\n"
        
        matches = re.finditer(regex, webpage)
        for m in matches:
            newEval = m.group(0)
        
        #Preparing Useful string
        start = r"var decrypt={d:function(){}};"
        eval = re.sub(r'(window)', 'decrypt', newEval)
        end = r";console.log('https:'+decrypt."+encrypted_src+");"
        
        data = start+eval+end
        p = subprocess.Popen(['node'], stdin=subprocess.PIPE, stdout=subprocess.PIPE)
        decrypted_src, stderr = p.communicate(data)
        return compat_str(decrypted_src)

    def _real_extract(self, url):
        video_id = self._match_id(url)
        
        webpage = self._download_webpage(url, video_id)

        title = self._og_search_title(webpage, default=video_id)
        
        formats = []
        for format_ in re.findall(r'({[^}]*\bsrc\s*:\s*[^}]*})', webpage):
            
            #Sanitizing before Parsing
            valid_json = re.sub(r'(type)',r'"\1"',format_)
            valid_json = re.sub(r'(src)', r'"\1"', valid_json)
            valid_json = re.sub(r'(d\(.*\))',r'"\1"',valid_json)
            valid_json = re.sub(r'(height)',r'"\1"',valid_json)
            valid_json = re.sub(r'(bitrate)',r'"\1"',valid_json)
            valid_json = re.sub(r'(width)',r'"\1"',valid_json)

            video = self._parse_json( valid_json, video_id, None, False)

            if not video:
                continue
            src = self._decrypt_url(webpage, video.get('src'))
            if not src:
                continue
            
            ext = determine_ext(src, default_ext=None)
            if video.get('type') == 'application/dash+xml' or ext == 'mpd':
                formats.extend(self._extract_mpd_formats(
                    src, video_id, mpd_id='dash', fatal=False))
            else:
                formats.append({
                    'url': src,
                    'ext': ext or 'mp4',
                    'width': int_or_none(video.get('width')),
                    'height': int_or_none(video.get('height')),
                    'tbr': int_or_none(video.get('bitrate')),
                })
        self._sort_formats(formats)

        return {
            'id': video_id,
            'url': url,
            'title': title,
            'formats': formats,
        }
