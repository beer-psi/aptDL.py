import unicodedata, re, os
# Unimplemented: 
# * Resolve-PathForced -> os.path.abspath()
# * Resolve-SileoQueryString -> is going to live in its own place
# * Write-Color
# * Format-InputData
# * Get-7zExec -> Uses python libraries for handling compression

def remove_illegal_filename_characters(value, replacement_character='_', allow_unicode=False):
    value = str(value)
    if allow_unicode:
        value = unicodedata.normalize('NFKC', value)
    else:
        value = unicodedata.normalize('NFKD', value).encode('ascii', 'ignore').decode('ascii')
    return re.sub(r'[\/\\<>:"|?*]', replacement_character, value).rstrip('.').rstrip()


def format_url(url):
    if not (url.startswith('http://') or url.startswith('https://')):
        url = 'https://' + url
    return url.rstrip('/')

def dos2unix(file):
    with open(os.path.abspath(file),'rw') as filec:
        content = filec.readlines()
        for line in content:
            filec.write(line + b'\n')

    

