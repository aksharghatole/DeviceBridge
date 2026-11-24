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
  a.fill('#name','Laptop'); a.click('#create'); expect(a.locator('#roomCode')).not_to_have_text(''); code=a.locator('#roomCode').inner_text(); expect(a.locator('#qr')).to_be_visible(); a.wait_for_function("document.querySelector('#qr').complete && document.querySelector('#qr').naturalWidth > 0")
  b.fill('#name','Phone'); b.fill('#roomInput',code); b.click('#joinForm button'); expect(a.locator('#recipient option')).to_have_text('Phone',timeout=15000); expect(b.locator('#recipient option')).to_have_text('Laptop',timeout=15000)
  a.fill('#message','Hello from laptop'); a.click('#sendText'); expect(b.locator('#activity')).to_contain_text('Hello from laptop'); b.fill('#message','Hello from phone'); b.click('#sendText'); expect(a.locator('#activity')).to_contain_text('Hello from phone')
  payload=bytes(range(256))*4096
  a.set_input_files('#files',{'name':'test.bin','mimeType':'application/octet-stream','buffer':payload}); a.click('#sendFiles'); b.get_by_role('button',name='Accept',exact=True).click(); expect(a.locator('#activity')).to_contain_text('Delivered',timeout=15000)
  with b.expect_download() as d: b.get_by_role('button',name='Download',exact=True).click()
  assert Path(d.value.path()).read_bytes()==payload
  a.set_input_files('#files',{'name':'decline.txt','mimeType':'text/plain','buffer':b'no'}); a.click('#sendFiles'); b.get_by_role('button',name='Decline',exact=True).click(); expect(a.locator('#activity')).to_contain_text('Declined or recipient busy'); b.click('#leave'); expect(a.locator('#recipient option')).to_have_text('No connected devices'); browser.close()
  print('PASS: QR image, pairing, bidirectional text, byte-identical 1 MiB download, decline, leave, mobile layout.')
finally:
 p.terminate();p.wait()
