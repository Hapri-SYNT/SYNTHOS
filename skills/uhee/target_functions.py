# skills/uhee/target_functions.py
# Target fungsi untuk evolusi UHEE — infiltrasi pendaftaran anti-bot

TARGET_FUNCTION_SOURCE = '''
import time
import random
import asyncio
from typing import Optional

async def infiltrate_registration(page, platform_url: str, identity: dict) -> bool:
    try:
        await page.goto(platform_url, wait_until="domcontentloaded", timeout=30000)
        await page.wait_for_timeout(random.randint(2000, 5000))
        for i in range(random.randint(1, 4)):
            await page.evaluate("window.scrollBy(0, 300)")
            await page.wait_for_timeout(random.randint(500, 1500))
        signup_selectors = [
            'a:has-text("Sign Up")', 'a:has-text("Register")', 'a:has-text("Daftar")',
            'button:has-text("Get Started")', 'button:has-text("Join Now")',
            'text=Sign Up', 'text=Register', 'text=Daftar'
        ]
        for selector in signup_selectors:
            try:
                element = await page.wait_for_selector(selector, timeout=5000)
                if element:
                    box = await element.bounding_box()
                    if box:
                        x = box['x'] + box['width'] * random.uniform(0.2, 0.8)
                        y = box['y'] + box['height'] * random.uniform(0.2, 0.8)
                        await page.mouse.move(x, y, steps=random.randint(5, 15))
                        await page.wait_for_timeout(random.randint(100, 500))
                        await element.click()
                        break
            except:
                continue
        await page.wait_for_timeout(random.randint(1000, 3000))
        form_fields = {
            'email': ['input[type="email"]', 'input[name="email"]', '#email', '#signup-email'],
            'username': ['input[name="username"]', '#username', '#signup-username'],
            'password': ['input[type="password"]', '#password', '#signup-password'],
        }
        for field, selectors in form_fields.items():
            value = identity.get(field, "")
            if not value:
                if field == "email":
                    value = identity.get("dna_id", "user") + "@qnd.ai"
                elif field == "username":
                    value = identity.get("dna_id", "user").lower()
                elif field == "password":
                    value = "QndEvo" + str(random.randint(1000, 9999))
            for sel in selectors:
                try:
                    input_el = await page.wait_for_selector(sel, timeout=3000)
                    if input_el:
                        await input_el.click()
                        await page.wait_for_timeout(random.randint(100, 300))
                        for char in value:
                            await input_el.type(char, delay=random.randint(50, 200))
                        break
                except:
                    continue
        try:
            consent_btn = await page.wait_for_selector('input[type="checkbox"], .consent-checkbox', timeout=3000)
            if consent_btn:
                await consent_btn.click()
        except:
            pass
        submit_selectors = ['button[type="submit"]', 'input[type="submit"]', 'button:has-text("Create Account")']
        for sel in submit_selectors:
            try:
                submit_btn = await page.wait_for_selector(sel, timeout=3000)
                if submit_btn:
                    await submit_btn.click()
                    break
            except:
                continue
        await page.wait_for_timeout(5000)
        captcha_indicators = ['iframe[src*="captcha"]', 'iframe[src*="hcaptcha"]', '.g-recaptcha']
        for indicator in captcha_indicators:
            if await page.query_selector(indicator):
                return False
        current_url = page.url
        if any(word in current_url.lower() for word in ['dashboard', 'welcome', 'success', 'login']):
            return True
        success_texts = ['account created', 'welcome', 'verify your email', 'pendaftaran berhasil']
        page_content = await page.content()
        if any(text in page_content.lower() for text in success_texts):
            return True
        return False
    except Exception as e:
        print(f"Infiltrasi gagal: {str(e)[:100]}")
        return False
'''
