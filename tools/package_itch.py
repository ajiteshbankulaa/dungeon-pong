"""Prepare itch uploads after staging and packing the browser runtime."""
from pathlib import Path
import shutil,zipfile,textwrap
root=Path(__file__).resolve().parents[1]
release=root/'dist/itch'
release.mkdir(exist_ok=True)
shutil.copy2(root/'dist/WhatReturns-Windows.zip',release)
web=root/'build/itch/whatreturns/build/web'
html=(web/'index.html').read_text(encoding='utf8')
start=html.index("    if platform.window.location.host.find('.itch.zone')")
end=html.index('    # preloader',start)
lines=html[start:html.index('    else:',start)].splitlines()[1:]
html=html[:start]+'\n'.join(line[4:] for line in lines)+'\n\n'+html[end:]
html=html.replace('Ready to start ! Please click/touch page','Click to begin What Returns')
with zipfile.ZipFile(release/'WhatReturns-Browser.zip','w',zipfile.ZIP_DEFLATED) as package:
    package.writestr('index.html',html)
    for name in ('favicon.png','whatreturns.apk'):package.write(web/name,name)
