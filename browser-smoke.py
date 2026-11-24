from playwright.sync_api import sync_playwright,expect
import subprocess, time, os
from pathlib import Path
p=subprocess.Popen(['node','server.cjs'],env={**os.environ,'ICE_SERVERS':'[]','PORT':'3418'})
try:
 time.sleep(.4)
 with sync_playwright() as pw:
  browser=pw.chromium.launch(args=['--no-sandbox'])
  a=browser.new_page(); b=browser.new_page(viewport={'width':390,'height':844},is_mobile=True,has_touch=True)
  for x in [a,b]:
   x.on('pageerror',lambda e:print('PAGE ERROR',e))
   x.goto('http://localhost:3418')
  a.click('#theme'); expect(a.locator('html')).to_have_attribute('data-theme','light'); a.reload(); expect(a.locator('html')).to_have_attribute('data-theme','light'); a.check('#historyEnabled'); b.check('#historyEnabled');
  a.fill('#name','Laptop'); a.click('#create'); expect(a.locator('#roomCode')).not_to_have_text(''); code=a.locator('#roomCode').inner_text(); expect(a.locator('#qr')).to_be_visible(); a.wait_for_function("document.querySelector('#qr').complete && document.querySelector('#qr').naturalWidth > 0")
  b.fill('#name','Phone'); b.fill('#roomInput',code); b.click('#joinForm button'); expect(a.locator('#recipient option')).to_have_text('Phone',timeout=15000); expect(b.locator('#recipient option')).to_have_text('Laptop',timeout=15000)
  a.fill('#message','Hello from laptop'); a.click('#sendText'); expect(b.locator('#activity')).to_contain_text('Hello from laptop'); b.fill('#message','Hello from phone'); b.click('#sendText'); expect(a.locator('#activity')).to_contain_text('Hello from phone')
  a.fill('#sharedNote','Room note from laptop'); expect(b.locator('#sharedNote')).to_have_value('Room note from laptop')
  b.fill('#sharedNote','Updated by phone'); expect(a.locator('#sharedNote')).to_have_value('Updated by phone')
  a.click('#diagnostics'); expect(a.locator('#diagnosticResult')).to_contain_text('Signaling: connected')
  a.context.grant_permissions(['clipboard-read','clipboard-write'])
  a.evaluate("navigator.clipboard.writeText('clipboard sample')")
  a.click('#pasteClipboard'); expect(a.locator('#message')).to_have_value('clipboard sample')
  a.click('#sendText'); expect(b.locator('#activity')).to_contain_text('clipboard sample')
  # Deliberately close one channel and require a fresh open connection before sending files.
  a.evaluate("window.testOldPeer = Array.from(peers.values())[0]; window.testOldPeer.dc.close()")
  deadline=time.monotonic()+20
  while time.monotonic()<deadline:
   if a.evaluate("() => Array.from(peers.values()).some(p => p !== window.testOldPeer && p.dc?.readyState === 'open')"): break
   time.sleep(.2)
  else: raise AssertionError("Peer did not reconnect with a new open channel")
  expect(b.locator('#recipient option')).to_have_text('Laptop',timeout=15000)
  expect(a.locator('#sharedNote')).to_have_value('Updated by phone')
  a.fill('#message','Recovered connection'); a.click('#sendText'); expect(b.locator('#activity')).to_contain_text('Recovered connection')
  payload=bytes(range(256))*4096
  a.set_input_files('#files',{'name':'test.bin','mimeType':'application/octet-stream','buffer':payload}); a.click('#sendFiles'); b.get_by_role('button',name='Accept',exact=True).click(); expect(a.locator('#activity')).to_contain_text('Delivered',timeout=15000)
  with b.expect_download() as d: b.get_by_role('button',name='Download',exact=True).click()
  assert Path(d.value.path()).read_bytes()==payload
  expect(b.locator('#activity')).to_contain_text('CRC32 verified')
  # Pause immediately after accepting a deliberately larger transfer.
  a.evaluate("() => { const old=window.setTimeout; window.testOriginalSetTimeout=old; }")
  a.set_input_files('#files',{'name':'pause.bin','mimeType':'application/octet-stream','buffer':payload*8})
  a.click('#sendFiles')
  # Schedule the pause at the first streaming task, before the first binary chunk.
  a.evaluate("() => { const original=stream; window.testOriginalStream=original; stream=(p,t)=>{ const result=original(p,t); if(t.pauseButton) togglePause(p,t); return result; }; }")
  b.get_by_role('button',name='Accept',exact=True).click()
  expect(a.get_by_role('button',name='Resume',exact=True)).to_be_visible()
  expect(b.locator('#activity')).to_contain_text('Paused by sender')
  a.click('button:has-text("Resume")')
  expect(b.locator('#activity .item').filter(has_text='pause.bin')).to_contain_text('CRC32 verified',timeout=30000)
  with b.expect_download() as paused_dl: b.locator('#activity .item').filter(has_text='pause.bin').get_by_role('button',name='Download',exact=True).click()
  assert Path(paused_dl.value.path()).read_bytes()==payload*8
  a.evaluate("() => { stream=window.testOriginalStream; }")
  expect(a.locator('#savedHistory')).to_contain_text('test.bin'); expect(b.locator('#savedHistory')).to_contain_text('test.bin')
  import base64
  png=base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/x3sAAAAASUVORK5CYII=')
  a.set_input_files('#files',{'name':'preview.png','mimeType':'image/png','buffer':png}); a.click('#sendFiles'); b.get_by_role('button',name='Accept',exact=True).click(); b.get_by_role('button',name='Preview',exact=True).click(); expect(b.locator('img.media-preview')).to_be_visible(); b.get_by_role('button',name='Hide preview',exact=True).click(); expect(b.locator('img.media-preview')).to_have_count(0)
  # Exercise the actual disk-write path using a controlled picker substitute.
  b.evaluate("() => { window.showSaveFilePicker = async () => (await navigator.storage.getDirectory()).getFileHandle('disk-test.bin',{create:true}); }")
  a.set_input_files('#files',{'name':'disk-test.bin','mimeType':'application/octet-stream','buffer':payload*4})
  a.click('#sendFiles'); b.get_by_role('button',name='Save to disk',exact=True).click()
  expect(b.locator('#activity .item').filter(has_text='disk-test.bin')).to_contain_text('Saved to disk',timeout=30000)
  expect(a.locator('#activity .item').filter(has_text='disk-test.bin')).to_contain_text('Delivered')
  assert b.evaluate("async () => { const f=await (await (await navigator.storage.getDirectory()).getFileHandle('disk-test.bin')).getFile(); const bytes=new Uint8Array(await f.arrayBuffer()); return bytes.length===4194304 && bytes.every((v,i)=>v===i%256); }")
  # Interrupt a memory transfer after the receiver has retained a verified prefix.
  a.evaluate("() => { window.recoveryOriginalStats=transferStats; transferStats=(act,n,total,verb)=>{window.recoveryOriginalStats(act,n,total,verb); const p=Array.from(peers.values())[0],t=p?.sending; if(t?.f.name==='recover.bin' && !t.paused && !window.didRecoveryPause && n>=1048576){window.didRecoveryPause=true;togglePause(p,t);} }; }")
  a.set_input_files('#files',{'name':'recover.bin','mimeType':'application/octet-stream','buffer':payload*8})
  a.click('#sendFiles'); b.get_by_role('button',name='Accept',exact=True).click()
  expect(a.get_by_role('button',name='Resume',exact=True)).to_be_visible()
  deadline=time.monotonic()+10
  while time.monotonic()<deadline:
   if b.evaluate("() => Array.from(peers.values())[0]?.receiving?.bytes>=1048576"): break
   time.sleep(.1)
  else: raise AssertionError("No partial bytes received before interruption")
  b.evaluate("() => Array.from(peers.values())[0].dc.close()")
  expect(b.locator('#activity .item').filter(has_text='recover.bin')).to_contain_text('retained for 5 minutes')
  expect(a.locator('#recipient option')).to_have_text('Phone',timeout=20000)
  expect(b.locator('#recipient option')).to_have_text('Laptop',timeout=20000)
  a.get_by_role('button',name='Resume interrupted',exact=True).click()
  expect(b.locator('#activity .item').filter(has_text='recover.bin')).to_contain_text('Resume from 1.0 MiB')
  b.get_by_role('button',name='Resume receiving',exact=True).click()
  item=b.locator('#activity .item').filter(has_text='recover.bin')
  expect(item).to_contain_text('CRC32 verified',timeout=30000)
  with b.expect_download() as recovered: item.get_by_role('button',name='Download',exact=True).click()
  assert Path(recovered.value.path()).read_bytes()==payload*8
  a.evaluate("() => { transferStats=window.recoveryOriginalStats; }")
  from zipfile import ZipFile
  with b.expect_download() as batch: b.click('#downloadZip')
  with ZipFile(batch.value.path()) as z:
   assert z.testzip() is None
   assert z.read('test.bin')==payload
   assert z.read('preview.png')==png
  import tempfile
  with tempfile.TemporaryDirectory() as temp:
   folder=Path(temp)/'sample-folder'; folder.mkdir(); (folder/'hello.txt').write_text('hello'); (folder/'nested').mkdir(); (folder/'nested'/'world.txt').write_text('world')
   a.set_input_files('#folder',str(folder)); expect(a.locator('#queue')).to_contain_text('sample-folder.zip')
   a.click('#sendFiles'); b.get_by_role('button',name='Accept',exact=True).click()
   item=b.locator('#activity .item').filter(has_text='sample-folder.zip')
   with b.expect_download() as folder_dl: item.get_by_role('button',name='Download',exact=True).click()
   with ZipFile(folder_dl.value.path()) as z:
    assert z.testzip() is None
    assert z.read('sample-folder/hello.txt')==b'hello'
    assert z.read('sample-folder/nested/world.txt')==b'world'
  b.click('#clearHistory'); expect(b.locator('#savedHistory')).to_contain_text('No saved file history')
  a.set_input_files('#files',{'name':'decline.txt','mimeType':'text/plain','buffer':b'no'}); a.click('#sendFiles'); b.get_by_role('button',name='Decline',exact=True).click(); expect(a.locator('#activity')).to_contain_text('Declined or recipient busy'); b.click('#leave'); expect(b.locator('#sharedNote')).to_have_value(''); expect(a.locator('#recipient option')).to_have_text('No connected devices'); b.evaluate("navigator.serviceWorker.ready")
  b.wait_for_function("navigator.serviceWorker.controller !== null")
  b.context.set_offline(True); b.reload(); expect(b.locator('#offlineBanner')).to_be_visible(); b.click('#create'); expect(b.locator('#notice')).to_contain_text('Connect to the internet')
  b.context.set_offline(False)
  # Test strict mode independently from the default compatibility flow.
  c=browser.new_page(); e=browser.new_page()
  for page in [c,e]:
   page.goto('http://localhost:3418'); page.check('#strictPairing'); page.on('dialog',lambda d:d.accept())
  c.fill('#name','Verified laptop'); c.click('#create'); expect(c.locator('#roomCode')).not_to_have_text('')
  e.fill('#name','Verified phone'); e.fill('#roomInput',c.locator('#roomCode').inner_text()); e.click('#joinForm button')
  expect(c.get_by_role('button',name='Verify code',exact=True)).to_be_visible(timeout=15000)
  expect(e.get_by_role('button',name='Verify code',exact=True)).to_be_visible(timeout=15000)
  assert c.locator('.pair-code').inner_text()==e.locator('.pair-code').inner_text()
  expect(c.locator('#recipient option')).to_have_text('No connected devices')
  c.fill('#message','Protected message'); expect(c.locator('#sendText')).to_be_disabled()
  c.get_by_role('button',name='Verify code',exact=True).click(); e.get_by_role('button',name='Verify code',exact=True).click()
  expect(c.locator('#recipient option')).to_have_text('Verified phone'); c.click('#sendText')
  expect(e.locator('#activity')).to_contain_text('Protected message')
  browser.close()
  print('PASS: QR image, pairing, bidirectional text, byte-identical 1 MiB download, decline, leave, mobile layout.')
finally:
 p.terminate();p.wait()
