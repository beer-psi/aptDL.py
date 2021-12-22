import posixpath, requests, re, gzip, bz2, shutil, plistlib
import lzma as xz
from debian_inspector import debcon 
from modules.helper import format_url
from modules.download import download, get_headers

class DebianRepo:
    def __init__(self, url, suites=None, components=None, auth={}, authjson=''):
        self.url = format_url(url)
        self.suites = suites
        self.components = components

        self.disturl = self._disturl()
        self.payment_endpoint = self._payment_endpoint() 
        self.authentication = self._authenticate(auth) if auth and self.payment_endpoint else {'authenticated': False}
        self.release = self._release()
        self.packages = self._packages()
    
    def get_dl_link(self, index):
        package_id = self.packages[index]['package']
        version = self.packages[index]['version']
        if 'tag' in self.packages[index] and 'cydia::commercial' in self.packages[index]['tag']:
            if self.authentication['authenticated'] and package_id in self.authentication['purchased']:
                r = requests.post(f"{self.payment_endpoint}/package/{package_id}/authorize_download", 
                    data={**self.authentication['data'], **{'version': version, 'repo': self.url}})
                return format_url(r.json()['url'].rstrip('\n'))
            else:
                return None
        else:
            return posixpath.join(self.url, self.packages[index]['filename'])
    
    def _disturl(self):
        if self.suites and self.suites != './':
            return format_url(f"{self.url}/dists/{self.suites}")
        else: 
            return self.url
    
    def _payment_endpoint(self):
        r = requests.get(f"{self.url}/payment_endpoint")
        if r.status_code == 200:
            return format_url(r.text.rstrip('\n'))
        else:
            return None
    
    def _authenticate(self, authentication):
        try:
            r = requests.post(f"{self.payment_endpoint}/user_info", data=authentication)
            if r.status_code == 200: 
                userdata = r.json()
                return {
                    'authenticated': True,
                    'data': authentication,
                    'username': userdata['user']['name'],
                    'purchased': userdata['items']
                }
        except:
            return {
                'authenticated': False
            }
    
    def _release(self):
        download(f"{self.disturl}/Release", './Release')
        release_content = list(debcon.get_paragraphs_data_from_file('./Release'))[0]
        for hash_method in ['md5sum', 'sha1', 'sha256', 'sha512']:
            if hash_method in release_content:
                hash_formatted = list()
                for line in release_content[hash_method].split('\n '):
                    value, size, filename = line.split()
                    hash_formatted.append({
                        'value': value,
                        'size': size,
                        'filename': filename,
                    })
                release_content[hash_method] = hash_formatted
        return release_content

    def _packages(self):
        # Determining compression methods
        magic_bits = {
            b'\x1f\x8b\x08': "gz",
            b'\x42\x5a\x68': "bz2",
            b'\xfd\x37\x7a\x58\x5a\x00': "xz"
        }
        magic_max_len = max(len(x) for x in magic_bits)

        release = self.release
        packages_filenames = list()
        for hash_method in ['md5sum', 'sha1', 'sha256', 'sha512']:
            if hash_method in release:
                packages_filenames += [x['filename'] for x in release.get(hash_method)]
        packages_regex = re.compile(r'Packages(?:\.(?:bz2|gz|xz))')
        packages_filenames = [i for i in list(set(packages_filenames)) if packages_regex.search(i)] or ['Packages.xz', 'Packages.bz2', 'Packages.gz', 'Packages']
        for packages in packages_filenames:
            try:
                packages = download(f"{self.disturl}/{packages}")
                with open(packages, 'rb') as f:
                    file_start = f.read(magic_max_len)
                for magic, filetype in magic_bits.items():
                    if file_start.startswith(magic):
                        if filetype == 'gz':
                            with gzip.open(packages, 'rb') as f_in:
                                with open('./Packages', 'wb') as f_out:
                                    shutil.copyfileobj(f_in, f_out)
                        elif filetype == 'bz2':
                            with bz2.open(packages, 'rb') as f_in:
                                with open('./Packages', 'wb') as f_out:
                                    shutil.copyfileobj(f_in, f_out)
                        elif filetype == 'xz':
                            with xz.open(packages, 'rb') as f_in:
                                with open('./Packages', 'wb') as f_out:
                                    shutil.copyfileobj(f_in, f_out)  
                break
            except:
                continue
        packages_content = list(debcon.get_paragraphs_data_from_file('./Packages'))    
        return packages_content

class InstallerRepo:
    def __init__(self, url):
        self.url = format_url(url)
        self.packages = self._packages()
    
    def get_dl_link(self, index):
        return self.packages[index]['filename']

    def _packages(self):
        download(self.url, './Packages.plist')
        with open('./Packages.plist', 'rb') as file:
            packages_content = plistlib.load(file).get('packages')
        replacement_keys = {
            'bundleIdentifier': 'package',
            'location': 'filename',
        }
        retval = list()
        for i in packages_content:
            retval.append({replacement_keys.get(k, k): v for k, v in i.items()})
        return retval