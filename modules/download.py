import sys, platform, posixpath, os, requests
from tqdm import tqdm
from modules.helper import remove_illegal_filename_characters

def get_headers(model="iPhone10,5", udid="0000000000000000000000000000000000000000", firmware="14.8"):
    pyinfo = f"Python/{'.'.join(map(str, sys.version_info[0:3]))}"
    sysinfo = f"{platform.system()} {platform.version()}; {platform.machine()}"
    headers = {
        "X-Machine": model,
        "X-Unique-ID": udid,
        "X-Firmware": firmware,
        "User-Agent": f"aptDL.py/1.0 (+https://github.com/extradummythicc/aptDL.py) {pyinfo} ({sysinfo})"
    }
    return headers

# Assumes destination doesnt have any invalid filename characters
def download(url, destination="", prepend=""):
    destination = os.path.abspath(destination) if destination else os.path.join('./', remove_illegal_filename_characters(posixpath.basename(url)))
    filename = os.path.basename(destination)
    try:
        with requests.get(url, headers=get_headers(), stream=True) as r:
            if not os.path.isdir(os.path.dirname(destination)):
                os.makedirs(os.path.dirname(destination))
            if r.status_code == 200:
                filesize = int(r.headers["Content-Length"])
                with open(destination, "wb") as f, tqdm(
                    unit="B",  # unit string to be displayed.
                    unit_scale=True,  # let tqdm to determine the scale in kilo, mega..etc.
                    unit_divisor=1000,  # is used when unit_scale is true
                    total=filesize,  # the total iteration.
                    file=sys.stdout,  # default goes to stderr, this is the display on console.
                    desc=f"{prepend} {filename}"  # prefix to be displayed on progress bar.
                ) as progress:
                    for chunk in r.iter_content(chunk_size=1024):
                        # download the file chunk by chunk
                        datasize = f.write(chunk)
                        # on each chunk update the progress bar.
                        progress.update(datasize)
            else:
                raise ConnectionError(f"Download for {filename} failed: {r.status_code}")
        return destination
    except KeyboardInterrupt:
        if os.path.isfile(destination):
            os.remove(destination)
        if len(os.listdir(os.path.dirname(destination))) == 0:
            os.remove(os.path.dirname(destination))



