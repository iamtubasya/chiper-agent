const { firefox } = require('playwright');
const fs = require('fs');
const path = require('path');

const SKILL_DIR = path.join(__dirname, '..');
const COOKIE_FILE = path.join(SKILL_DIR, 'cookie.json');
const ACCOUNT_FILE = path.join(SKILL_DIR, 'account.txt');
const SCREENSHOT_DIR = path.join(SKILL_DIR, 'screenshots');
const PROFILE_DIR = path.join(SKILL_DIR, 'browser-profile');

fs.mkdirSync(SCREENSHOT_DIR, { recursive: true });
fs.mkdirSync(PROFILE_DIR, { recursive: true });

function loadAccount() {
    if (!fs.existsSync(ACCOUNT_FILE)) return null;
    try {
        const lines = fs.readFileSync(ACCOUNT_FILE, 'utf8').trim().split('\n');
        const acc = {};
        for (const line of lines) {
            const [k, ...v] = line.split(':');
            const val = v.join(':').trim();
            if (k.trim().toLowerCase() === 'username') acc.username = val.replace(/^@/, '');
            if (k.trim().toLowerCase() === 'password') acc.password = val;
        }
        return (acc.username && acc.password) ? acc : null;
    } catch { return null; }
}

function saveCookie(cookies) {
    const auth = cookies.find(c => c.name === 'auth_token');
    const ct0 = cookies.find(c => c.name === 'ct0');
    if (!auth || !ct0) return false;
    fs.writeFileSync(COOKIE_FILE, JSON.stringify({
        auth_token: auth.value, ct0: ct0.value, created_at: new Date().toISOString()
    }, null, 2));
    fs.chmodSync(COOKIE_FILE, 0o600);
    return true;
}

async function typeHuman(page, text, delay = 80) {
    for (const char of text) {
        await page.keyboard.press(char);
        await new Promise(r => setTimeout(r, delay + Math.random() * 40));
    }
}

(async () => {
    const account = loadAccount();
    if (!account) {
        console.log('ERROR: Account tidak ditemukan. Buat account.txt dulu.');
        process.exit(1);
    }

    console.log('Login sebagai @' + account.username + '...');

    const ctx = await firefox.launchPersistentContext(PROFILE_DIR, {
        headless: true,
        viewport: { width: 1366, height: 768 },
        locale: 'en-US',
        timezoneId: 'Asia/Jakarta',
        firefoxUserPrefs: { 'dom.webdriver.enabled': false }
    });

    const page = ctx.pages()[0] || await ctx.newPage();

    // Step 1: Load login
    await page.goto('https://x.com/i/flow/login', { waitUntil: 'load', timeout: 45000 });
    await new Promise(r => setTimeout(r, 5000 + Math.random() * 3000));

    let input = await page.$('input[name="username_or_email"]') || await page.$('input[type="text"]');
    if (!input) { console.log('ERROR: Input tidak ditemukan'); await ctx.close(); process.exit(1); }

    // Step 2: Username
    await input.click({ force: true });
    await input.fill('');
    await typeHuman(page, account.username);
    await new Promise(r => setTimeout(r, 800));
    await page.keyboard.press('Enter');
    await new Promise(r => setTimeout(r, 5000));

    // Step 3: Password
    let pwd = await page.$('input[name="password"]') || await page.$('input[type="password"]');
    if (!pwd) { console.log('ERROR: Password field tidak ditemukan'); await ctx.close(); process.exit(1); }

    await pwd.click({ force: true });
    await pwd.fill('');
    await typeHuman(page, account.password);
    await new Promise(r => setTimeout(r, 800));
    await page.keyboard.press('Enter');
    await new Promise(r => setTimeout(r, 10000));

    // Step 4: Check result
    const url = page.url();

    if (url.includes('/home') || url.includes('/explore')) {
        console.log('LOGIN BERHASIL!');
        const cookies = await ctx.cookies();
        if (saveCookie(cookies)) {
            console.log('Cookie saved: ' + COOKIE_FILE);
        }
        await ctx.close();
        process.exit(0);
    }

    // Check for verification
    const content = await page.content();
    if (content.includes('verify_code') || content.includes('Preparing verification') || content.includes('captcha') || content.includes('Arkose')) {
        console.log('VERIFICATION_DIPERLUKAN');
        await ctx.close();
        process.exit(2);
    }

    if (content.includes('temporarily limited')) {
        console.log('RATE_LIMITED');
        await ctx.close();
        process.exit(3);
    }

    if (content.includes('incorrect') || content.includes('wrong')) {
        console.log('PASSWORD_SALAH');
        await ctx.close();
        process.exit(4);
    }

    if (content.includes('suspended')) {
        console.log('ACCOUNT_SUSPENDED');
        await ctx.close();
        process.exit(5);
    }

    console.log('LOGIN_GAGAL');
    await ctx.close();
    process.exit(1);
})().catch(e => { console.log('FATAL: ' + e.message); process.exit(1); });
