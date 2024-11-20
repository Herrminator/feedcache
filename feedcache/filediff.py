import os

#-----------------------------------------------------------------------------
def diff_diff(left, right):
  import subprocess
  result = subprocess.run([ "diff", left, right ], stdout=subprocess.DEVNULL)
  return result.returncode

def difflib_diff(left, right):
  raise NotImplementedError("TODO")
  
def filecmp_diff(left, right):
  import filecmp
  return 0 if filecmp.cmp(left, right, shallow=False) else 1
  
differ = filecmp_diff

def normalize_CR(text):
  return text.replace('\r\n', '\n').replace('\r', '\n')

def diff(left, right, ldata=None, rdata=None, ignore=None):
  """ 0: equal, > 0 different, < 0 ignored differences """
  if     os.path.isfile(left) != os.path.isfile(right): return 1
  if not os.path.isfile(left): return 1 # treat non-existant as different

  if ignore is None:
    return differ(left, right)

  # compare content
  if ldata is None:
    with open(left, encoding="utf-8")  as f: ldata = f.read()
  if rdata is None:
    with open(right, encoding="utf-8") as f: rdata = f.read()

  if ldata == rdata: return 0

  rdata, ldata = normalize_CR(ignore.sub("", ldata)), normalize_CR(ignore.sub("", rdata))

  return -1 if ldata == rdata else 1
