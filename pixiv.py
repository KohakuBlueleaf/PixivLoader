#native lib
import os,sys
from time import sleep,time
import threading as th
from random import random as rand

#selenium / urllib
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import urllib.request
import urllib.error


#載入cookies/header
import pickle
from headers import headers

#載入預先得到的cookies
with open('cookie.pydict', 'rb') as f:
	cookies = pickle.load(f)


#設定圖片下載器
opener = urllib.request.build_opener()
opener.addheaders = headers
urllib.request.install_opener(opener)
	
def download(url, file_name):
	try:
		urllib.request.urlretrieve(url, file_name+'.jpg')
	except:
		try:
			urllib.request.urlretrieve(url.replace('.jpg','.png'), file_name+'.png')
		except:
			pass


#設定pixiv爬蟲物件
class pixiv:
	#start the driver
	def __init__(self, cookies):
		print('Initialize...', end='\r', flush=True)
		#創建chrome設定
		chrome_options = Options()
		
		#不打開視窗
		chrome_options.add_argument("--headless")
		
		#避免多餘的提示訊息
		chrome_options.add_argument("--disable-extensions")
		chrome_options.add_argument("--silent")
		chrome_options.add_argument("--log-level=3")
		
		#創建driver (兩行分別為linux/windows使用)
		if sys.platform=='linux':
			driver = webdriver.Chrome(executable_path="./chromedriver", options=chrome_options)
		elif sys.platform=='win32':
			driver = webdriver.Chrome(executable_path="./chromedriver.exe", options=chrome_options)
		driver.set_window_size(1051, 815)
		
		#先連接到pixiv主站並刪除所有cookies
		driver.get('https://www.pixiv.net')
		driver.delete_all_cookies()
			
		#添加cookies
		for cookie in cookies:
			cookie.pop('expiry',None)
			driver.add_cookie(cookie)
		
		self.driver = driver
		
		print('\ndone!')
	
	
	def download(self, pic_id, path='./image/pic/{}', afile=True, wait=False):
		url='https://www.pixiv.net/artworks/'
		pic_id = str(pic_id)
		
		#確認輸入的為網址還是ID
		if pic_id.isdigit():
			pass
		else:
			pic_id = pic_id.split('/')[-1]
		
		#若afile為true則輸出到單獨資料夾
		if afile:
			path = path.format(pic_id+'/{}')
			if not os.path.isdir(path.format('')):
				os.mkdir(path.format(''))
		
		#進入該頁面並等待渲染
		self.driver.get(url + pic_id)
		sleep(0.3)
	
		#獲取圖片網址
		img = [i for i in self.driver.find_elements_by_tag_name('img') if i.get_attribute('srcset')]
		img = img[0].get_attribute('srcset').split(',')[-1]
		img = img.replace('_master1200','').replace('-master','-original')
		print(img)
		spans = self.driver.find_elements_by_tag_name('span')
		
		#獲取圖片數量
		amount = 1
		for i in spans:
			text = i.text
			this = text.split('/')
			if len(this)==2 and this[1].isdigit():
				amount = int(this[1])
				break
		
		#使用threading批量下載
		pool = []
		for i in range(amount):
			url = img.replace(f'p0',f'p{i}')
			pool.append(th.Thread(target = download, args=(url, path.format(pic_id+f'_{i}'))))
			pool[i].start()
		
		#若wait則等待所有圖片下載完成
		if wait:
			for i in pool:
				i.join()
	
	
	def load_from_bookmark(self, uid, s_page=1, e_page=1):
		uid = str(uid)
		
		#確認輸入的為網址還是ID
		if uid.isdigit():
			url = f'https://www.pixiv.net/users/{uid}/bookmarks/artworks' + '?p={}'
		else:
			uid = uid.replace('https://','')
			uid = uid.split('/')[2]
			url = f'https://www.pixiv.net/users/{uid}/bookmarks/artworks' + '?p={}'
		
		
		#針對收藏頁創建資料夾
		u_dir = './image/bookmark_{}'.format(uid)
		if not os.path.isdir(u_dir):
			os.mkdir(u_dir)
		
		
		#獲取收藏頁
		for i in range(s_page,e_page+1):
			T0 = time()
			print('page{}...'.format(i))
			
			#進入收藏頁面並等待渲染
			self.driver.get(url.format(i))
			sleep(0.5)
			
			#滑動頁面以刷新圖片
			for i in range(30):
				self.driver.execute_script("window.scrollTo({},{})".format(i*50,i*200))
				sleep(0.01)
			
			#檢查所有a物件 並將屬於圖片的物件網址加入list
			a = self.driver.find_elements_by_tag_name('a')
			a = [i for i in a if i.get_attribute('href').count('/artworks/')]
			a = [a[i] for i in range(0,96,2)]
			if not a:
				break
			
			#檢查a物件底下的span 如果有即為2張以上 確認後從中獲取數量
			span = [i.find_elements_by_tag_name('span') for i in a]
			amounts = []
			for s in span:
				if s:
					amounts.append(int(s[2].text))
				else:
					amounts.append(1)
			
			#獲取所有的圖片訊息
			imgs = [i.find_element_by_tag_name('img').get_attribute('src') for i in a]
			img = ['https://i.pximg.net/img-original'+i[i.find('/img/'):i.find('p0')+1]+'{}.jpg' for i in imgs]
			
			#批量下載
			pool = []
			for k in range(len(a)):
				iurl = img[k]
				pic_id = iurl.split('/')[-1].split('_p')[0]
				path = u_dir+'/{}'.format(pic_id)+'_p{}.jpg'
				
				for j in range(amounts[k]):
					try:
						pool.append(th.Thread(target = download, args=(iurl.format(j), path.format(j))))
					except:
						continue
			
			for t in pool:
				t.start()
			
			#為避免網路錯誤 等待所有下載線程結束後再往下一頁
			for t in pool:
				t.join()
				
			print('Cost: {}s'.format(time()-T0))
	
	
	def load_from_author(self, uid, s_page=1, e_page=1, mode=0):
		manga = bool(mode)
		mode = ('illustrations', 'manga')[mode]
		uid = str(uid)
		
		#確認輸入的為網址還是ID
		if uid.isdigit():
			url = f'https://www.pixiv.net/users/{uid}/{mode}' + '?p={}'
		else:
			uid = uid.replace('https://','')
			uid = uid.split('/')[2]
			url = f'https://www.pixiv.net/users/{uid}/{mode}' + '?p={}'
		
		
		#針對作品頁創建資料夾
		u_dir = './image/author_{}'.format(uid)
		if not os.path.isdir(u_dir):
			os.mkdir(u_dir)
		
		
		#獲取作品頁
		for i in range(s_page,e_page+1):
			T0 = time()
			print('page{}...'.format(i))
			
			#進入作品頁面並等待渲染
			self.driver.get(url.format(i))
			sleep(0.5)
			
			#滑動頁面以刷新圖片
			for i in range(30):
				self.driver.execute_script("window.scrollTo({},{})".format(i*50,i*200))
				sleep(0.01)
			
			#檢查所有a物件 並將屬於圖片的物件網址加入list
			a = self.driver.find_elements_by_tag_name('a')
			a = [i for i in a if i.get_attribute('href').count('/artworks/')]
			a = [a[i] for i in range(0,len(a),2)]
			if not a:
				break
			
			#檢查a物件底下的span 如果有即為2張以上 確認後從中獲取數量
			span = [i.find_elements_by_tag_name('span') for i in a]
			amounts = []
			for s in span:
				if s:
					amounts.append(int(s[2].text))
				else:
					amounts.append(1)
			
			#獲取所有的圖片訊息
			imgs = [i.find_element_by_tag_name('img').get_attribute('src') for i in a]
			img = ['https://i.pximg.net/img-original'+i[i.find('/img/'):i.find('p0')+1]+'{}.jpg' for i in imgs]
			
			#批量下載
			pool = []
			for k in range(len(a)):
				iurl = img[k]
				pic_id = iurl.split('/')[-1].split('_p')[0]
				
				if manga:
					path = u_dir+'/{}/'.format(pic_id)
					if not os.path.isdir(path):
						os.mkdir(path)
					path += 'page{}.jpg'
				else:
					path = u_dir+'/{}'.format(pic_id)+'_p{}.jpg'
				
				for j in range(amounts[k]):
					try:
						pool.append(th.Thread(target = download, args=(iurl.format(j), path.format(j))))
					except:
						continue
			
			for t in pool:
				t.start()
			
			#為避免網路錯誤 等待所有下載線程結束後再往下一頁
			for t in pool:
				t.join()
				
			print('Cost: {}s'.format(time()-T0))
		
		
	def load_from_tags(self, tags, mode=0, s_page=1, e_page=1):
		#建立tag資料夾及搜尋網址
		t_dir = './image/tag_{}'.format('_'.join(tags.split()))
		tags = '%20'.join(tags.split())
		url = 'https://www.pixiv.net/tags/{}/artworks'+['?','?order=date','?order=popular_d'][mode]+'&p={}&s_mode=s_tag'
		
		#如果資料夾不存在則新增
		if not os.path.isdir(t_dir):
			os.mkdir(t_dir)
		
		
		#獲取tag頁
		for i in range(s_page,e_page+1):
			T0 = time()
			print('page{}...'.format(i))
			
			#進入收藏頁面並等待渲染
			self.driver.get(url.format(tags, i))
			sleep(0.5)
			
			#滑動頁面以刷新圖片
			for i in range(30):
				self.driver.execute_script("window.scrollTo({},{})".format(i*50,i*200))
				sleep(0.01)
			
			#檢查所有a物件 並將屬於圖片的物件網址加入list
			a = self.driver.find_elements_by_tag_name('a')
			a = [i for i in a if i.get_attribute('href').count('/artworks/')]
			a = [a[i] for i in range(1,len(a),2)]
			if not a:
				break
			
			#檢查a物件底下的span 如果有即為2張以上 確認後從中獲取數量
			span = [i.find_elements_by_tag_name('span') for i in a]
			amounts = []
			for s in span:
				if s:
					amounts.append(int(s[2].text))
				else:
					amounts.append(1)
			
			#獲取所有的圖片訊息
			imgs = [i.find_element_by_tag_name('img').get_attribute('src') for i in a]
			img = ['https://i.pximg.net/img-original'+i[i.find('/img/'):i.find('p0')+1]+'{}.jpg' for i in imgs]
			
			#批量下載
			pool = []
			for k in range(len(a)):
				iurl = img[k]
				pic_id = iurl.split('/')[-1].split('_p')[0]
				
				path = t_dir+'/{}'.format(pic_id)+'_p{}.jpg'
				
				for j in range(amounts[k]):
					try:
						pool.append(th.Thread(target = download, args=(iurl.format(j), path.format(j))))
					except:
						continue
			
			for t in pool:
				t.start()
			
			#為避免網路錯誤 等待所有下載線程結束後再往下一頁
			for t in pool:
				t.join()
				
			print('Cost: {}s'.format(time()-T0))
	
	def save_cookies(self):
		cookies = self.driver.get_cookies()
		with open('./cookie.pydict','wb') as f:
			pickle.dump(cookies,f)
	


if __name__ == '__main__':
	loader = pixiv(cookies)
	while True:
		mode = input('選擇下載模式：\n1.圖片網址\n2.個人收藏\n3.搜尋作者\n4.搜尋tag\n5.儲存cookies\nq.離開\n: ')
		if mode == '1':
			url = input('請輸入圖片網址/id或輸入q離開\n: ')
			while url!='q':
				loader.download(url,wait = True)
				url = input('請輸入圖片網址/id或輸入q離開\n: ')
		
		elif mode == '2':
			uid = input('請輸入uid或個人資料頁面的網址或輸入q離開\n: ')
			while uid!='q':
				print('一頁總共有48個項目')
				s_page = int(input('從第幾頁開始下載: '))
				e_page = int(input('下載完哪一頁結束: '))
				loader.load_from_bookmark(uid, s_page, e_page)
				uid = input('請輸入uid或個人資料頁面的網址或輸入q離開\n: ')
				
		elif mode == '3':
			uid = input('請輸入uid或作者作品頁面的網址或輸入q離開\n: ')
			while uid!='q':
				mode = int(input('請輸入項目(1.插畫, 2.漫畫): '))-1
				print('一頁總共有48個項目')
				s_page = int(input('從第幾頁開始下載: '))
				e_page = int(input('下載完哪一頁結束: '))
				loader.load_from_author(uid, s_page, e_page, mode)
				uid = input('請輸入uid或作者作品頁面的網址或輸入q離開\n: ')
				
		elif mode == '4':
			tags = input('請輸入搜尋標籤（多個請以空格隔開）或輸入q離開\n: ')
			while tags!='q':
				mode = int(input('選擇搜尋模式(1.從新, 2.從舊, 3.人氣): '))-1
				print('一頁總共有60個項目')
				s_page = int(input('從第幾頁開始下載: '))
				e_page = int(input('下載完哪一頁結束: '))
				loader.load_from_tags(tags, mode, s_page, e_page)
				tags = input('請輸入搜尋標籤（多個請以空格隔開）或輸入q離開\n: ')
		
		elif mode == '5':
			loader.save_cookies()
		else:
			break
			
	loader.driver.quit()
