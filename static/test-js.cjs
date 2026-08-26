const puppeteer = require('puppeteer');

(async () => {
    const browser = await puppeteer.launch({ headless: 'new' });
    const page = await browser.newPage();
    
    // 监听 console
    page.on('console', msg => {
        console.log(`[BROWSER ${msg.type()}] ${msg.text()}`);
    });
    
    // 监听未捕获的错误
    page.on('pageerror', err => {
        console.log(`[BROWSER ERROR] ${err.toString()}`);
    });

    console.log('Navigating to app...');
    await page.goto('http://localhost:5173', { waitUntil: 'networkidle0' });
    
    // 打开邮箱
    await page.waitForSelector('.mailbox-icon-container button');
    await page.click('.mailbox-icon-container button');
    
    await new Promise(r => setTimeout(r, 1000));
    
    // 找到 HTML 应用并点击
    const htmlAppIcons = await page.$$('.desktop-icon');
    for (const icon of htmlAppIcons) {
        const text = await icon.evaluate(el => el.textContent);
        if (text && text.includes('修仙')) {
            console.log('Clicking HtmlApp icon:', text);
            await icon.click();
            break;
        }
    }
    
    await new Promise(r => setTimeout(r, 2000));
    
    // 尝试点击应用内的按钮
    const frames = await page.frames();
    const htmlFrame = frames.find(f => f.url().startsWith('blob:'));
    if (htmlFrame) {
        console.log('Found HTML app iframe, clicking buttons...');
        const buttons = await htmlFrame.$$('button, .button, [role="button"]');
        for (const btn of buttons) {
            try {
                const text = await btn.evaluate(el => el.textContent);
                console.log('Clicking inside HTML frame:', text);
                await btn.click();
                await new Promise(r => setTimeout(r, 500));
            } catch (e) {
               console.log('Click error:', e.message);
            }
        }
    } else {
        console.log('No Blob iframe found =(');
    }
    
    await new Promise(r => setTimeout(r, 1000));
    await browser.close();
})();
