const { firefox } = require('playwright');
const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');

const SKILL_DIR = path.join(__dirname, '..');
const COOKIE_FILE = path.join(SKILL_DIR, 'cookie.json');
const ACCOUNT_FILE = path.join(SKILL_DIR, 'account.txt');
const GMAIL_FILE = path.join(SKILL_DIR, 'gmail-app.txt');
const SCREENSHOT_DIR = path.join(SKILL_DIR, 'screenshots');

fs.mkdirSync(SCREENSHOT_DIR, { recursive: true });

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

function getVerificationCode() {
    try {
        const result = execSync('himalaya envelope list --page-size 10 --output json 2>/dev/null',
            { encoding: 'utf8', timeout: 15000 });
        const envelopes = JSON.parse(result);

        for (const env of envelopes) {
            const from = (env.from && env.from.addr) ? env.from.addr.toLowerCase() : '';
            const subject = env.subject || '';

            if (from.includes('x.com') || from.includes('twitter.com')) {
                const codeMatch = subject.match(/(\d{6})/);
                if (codeMatch) return codeMatch[1];
            }
        }
        return null;
    } catch { return null; }
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

    console.log('Login via Tor sebagai @' + account.username + '...');

    const browser = await firefox.launch({
        headless: true,
        proxy: { server: 'socks5://127.0.0.1:9050' },
        firefoxUserPrefs: { 'dom.webdriver.enabled': false }
    });

    const context = await browser.newContext({
        viewport: { width: 1366, height: 768 },
        locale: 'en-US',
        timezoneId: 'Asia/Jakarta'
    });

    const page = await context.newPage();
    await page.addInitScript(() => { Object.defineProperty(navigator, 'webdriver', { get: () => undefined }); });

    // Step 1: Load login
    console.log('Step 1: Loading login page...');
    await page.goto('https://x.com/i/flow/login', { waitUntil: 'load', timeout: 60000 });
    await new Promise(r => setTimeout(r, 8000));

    let input = await page.$('input[name="username_or_email"]') || await page.$('input[type="text"]');
    if (!input) { console.log('ERROR: Input tidak ditemukan'); await browser.close(); process.exit(1); }

    // Step 2: Username
    await input.click({ force: true });
    await input.fill('');
    await typeHuman(page, account.username);
    await new Promise(r => setTimeout(r, 800));
    await page.keyboard.press('Enter');
    console.log('Step 2: Username submitted');
    await new Promise(r => setTimeout(r, 6000));

    // Step 3: Password
    let pwd = await page.$('input[name="password"]') || await page.$('input[type="password"]');
    if (!pwd) { console.log('ERROR: Password field tidak ditemukan'); await browser.close(); process.exit(1); }

    await pwd.click({ force: true });
    await pwd.fill('');
    await typeHuman(page, account.password);
    await new Promise(r => setTimeout(r, 800));
    await page.keyboard.press('Enter');
    console.log('Step 3: Password submitted');
    await new Promise(r => setTimeout(r, 15000));

    // Step 4: Check result
    let url = page.url();
    console.log('URL: ' + url);

    // Langsung berhasil?
    if (url.includes('/home') || url.includes('/explore')) {
        console.log('LOGIN BERHASIL! (tanpa verifikasi)');
        const cookies = await context.cookies();
        if (saveCookie(cookies)) {
            console.log('Cookie saved: ' + COOKIE_FILE);
        }
        await browser.close();
        process.exit(0);
    }

    // Step 5: Deteksi verifikasi
    const content = await page.content();
    const needsVerify = content.includes('verify_code') || 
                        content.includes('Preparing verification') || 
                        content.includes('captcha') || 
                        content.includes('Arkose') ||
                        url.includes('verify');

    if (!needsVerify) {
        // Cek error lain
        if (content.includes('temporarily limited')) console.log('RATE_LIMITED');
        else if (content.includes('incorrect') || content.includes('wrong')) console.log('PASSWORD_SALAH');
        else if (content.includes('suspended')) console.log('ACCOUNT_SUSPENDED');
        else console.log('LOGIN_GAGAL');
        await browser.close();
        process.exit(1);
    }

    // Step 6: Verifikasi diperlukan — ambil kode dari email
    console.log('Step 4: Verifikasi diperlukan, mengambil kode dari email...');

    // Tunggu email masuk
    await new Promise(r => setTimeout(r, 5000));

    let code = null;
    let attempts = 0;
    while (!code && attempts < 5) {
        code = getVerificationCode();
        if (!code) {
            attempts++;
            console.log('  Menunggu kode verifikasi... (attempt ' + attempts + '/5)');
            await new Promise(r => setTimeout(r, 5000));
        }
    }

    if (!code) {
        console.log('ERROR: Kode verifikasi tidak ditemukan di email');
        await page.screenshot({ path: path.join(SCREENSHOT_DIR, 'tor_verify_failed.jpg'), type: 'jpeg' });
        await browser.close();
        process.exit(1);
    }

    console.log('Step 5: Kode ditemukan: ' + code);

    // Step 7: Submit kode
    let verifyInput = await page.$('input[data-testid="ocfEnterTextTextInput"]')
        || await page.$('input[name="text"]')
        || await page.$('input[type="text"]');

    if (!verifyInput) {
        // Cari semua input
        const allInputs = await page.$$('input');
        if (allInputs.length > 0) verifyInput = allInputs[0];
    }

    if (verifyInput) {
        await verifyInput.click({ force: true });
        await verifyInput.fill('');
        await typeHuman(page, code);
        await new Promise(r => setTimeout(r, 800));
        await page.keyboard.press('Enter');
        console.log('Step 6: Kode submitted');
        await new Promise(r => setTimeout(r, 10000));

        url = page.url();
        console.log('URL: ' + url);
    }

    // Step 8: Check final result
    if (url.includes('/home') || url.includes('/explore')) {
        console.log('LOGIN BERHASIL! (dengan verifikasi)');
        const cookies = await context.cookies();
        if (saveCookie(cookies)) {
            console.log('Cookie saved: ' + COOKIE_FILE);
        }
        await browser.close();
        process.exit(0);
    }

    console.log('LOGIN_GAGAL setelah verifikasi');
    await page.screenshot({ path: path.join(SCREENSHOT_DIR, 'tor_final_failed.jpg'), type: 'jpeg' });
    await browser.close();
    process.exit(1);
})().catch(e => { console.log('FATAL: ' + e.message); process.exit(1); });
