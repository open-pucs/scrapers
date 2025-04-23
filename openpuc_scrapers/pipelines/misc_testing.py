from selenium import webdriver
from selenium.webdriver.support.wait import WebDriverWait


def test_selenium_connection() -> bool:
    """Test Selenium connectivity with enhanced error handling"""
    options = webdriver.ChromeOptions()
    options.add_argument("--headless=new")  # Use modern headless mode
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--remote-debugging-port=9222")
    options.add_argument(
        "--user-data-dir=/tmp/chrome-test-profile"
    )  # Unique profile dir

    try:
        driver = webdriver.Chrome(options=options)
        driver.get("https://www.google.com")
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.NAME, "q")))
        driver.quit()
        return True
    except Exception as e:
        print(f"Selenium error: {str(e)}")
        try:
            driver.quit()
        except Exception:
            pass
        return False
