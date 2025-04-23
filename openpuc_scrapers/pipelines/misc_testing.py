from selenium import webdriver
from selenium.webdriver.support.wait import WebDriverWait


def test_selenium_connection() -> bool:
    """Test Selenium connectivity with enhanced error handling"""
    options = webdriver.FirefoxOptions()
    options.add_argument("--headless")
    # Firefox generally needs fewer special flags
    options.add_argument("--disable-dev-shm-usage")

    try:
        driver = webdriver.Firefox(options=options)
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
