from selenium import webdriver

# 启动浏览器
driver = webdriver.Chrome()

# 打开一个页面
driver.get('http://xhslink.com/C/AHPEex')

# 获取当前页面的 URL
current_url = driver.current_url
print(current_url)

# 关闭浏览器
driver.quit()