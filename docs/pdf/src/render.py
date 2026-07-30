import asyncio, os
from playwright.async_api import async_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.abspath(os.path.join(HERE, '..'))
os.makedirs(OUT, exist_ok=True)

FOOTER = (
    '<div style="width:100%;font-size:7pt;color:#8a8a93;padding:0 15mm;'
    'font-family:-apple-system,Helvetica,sans-serif;display:flex;">'
    '<span>{left}</span>'
    '<span style="margin-left:auto">Page <span class="pageNumber"></span> '
    'of <span class="totalPages"></span></span>'
    '</div>'
)
EMPTY = '<div></div>'

JOBS = [
    {
        'html': 'runbook.html',
        'pdf': 'library-system-deployment-runbook.pdf',
        'footer': FOOTER.format(left='Library System — Deployment Runbook'),
        'margin': {'top': '16mm', 'bottom': '18mm', 'left': '15mm', 'right': '15mm'},
    },
    {
        'html': 'salesheet.html',
        'pdf': 'library-system-overview.pdf',
        'footer': FOOTER.format(left='Library System — Overview'),
        'margin': {'top': '12mm', 'bottom': '14mm', 'left': '12mm', 'right': '12mm'},
    },
]


async def main():
    async with async_playwright() as p:
        # Honour PLAYWRIGHT_BROWSERS_PATH / a preinstalled Chromium if one is
        # configured; otherwise use whatever `playwright install chromium` put down.
        exe = os.environ.get('CHROMIUM_PATH')
        browser = await (p.chromium.launch(executable_path=exe) if exe
                         else p.chromium.launch())
        page = await browser.new_page()
        for job in JOBS:
            await page.goto('file://' + os.path.join(HERE, job['html']))
            await page.wait_for_load_state('networkidle')
            await page.emulate_media(media='print')
            out = os.path.join(OUT, job['pdf'])
            await page.pdf(
                path=out,
                format='A4',
                print_background=True,
                display_header_footer=True,
                header_template=EMPTY,
                footer_template=job['footer'],
                margin=job['margin'],
            )
            print('wrote', out, os.path.getsize(out), 'bytes')
        await browser.close()

asyncio.run(main())
