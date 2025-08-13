import subprocess


# This works and introduces no fucking errors
def test_selenium_connection_exec() -> None:
    subprocess.run(
        """python -c "from selenium import webdriver; options = webdriver.FirefoxOptions(); options.add_argument('--headless'); driver = webdriver.Firefox(options=options); driver.get('https://www.google.com'); driver.quit(); print('\n\n*** Firefox driver test successful! ***\n')"""
    )


def test_selenium_connection_no_exception() -> bool:
    # If this works I am going to <REDACTED>
    from selenium import webdriver
    from selenium.webdriver.support.wait import WebDriverWait

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


def test_selenium_connection_fallible():
    from selenium import webdriver
    from selenium.webdriver.support.wait import WebDriverWait

    options = webdriver.FirefoxOptions()
    options.add_argument("--headless")
    # Firefox generally needs fewer special flags
    options.add_argument("--disable-dev-shm-usage")

    driver = webdriver.Firefox(options=options)
    driver.get("https://www.google.com")
    # WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.NAME, "q")))
    driver.quit()
