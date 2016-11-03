import cv2
import numpy as np
import statistics
import math
from util import *
import detect_line as dl

# If executed directly
def run_direct():
	original_img = cv2.imread('test/line_testing/test2.png')
	grayscale_img = cv2.cvtColor(original_img, cv2.COLOR_BGR2GRAY)
	(_, im_bw) = cv2.threshold(grayscale_img, 128, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)
	(x, y) = im_bw.shape

	essay = dl.output_line_imgs(im_bw)
	save_essay(essay)

# Returns all the candidate letter points as a list of pairs and max width of letter
# Return value:
#		( maximum width of a letter in the line,
#				[ word1, word2, word3, ... , wordN ] )
# wordN ::= [ letter1, letter2, ... , letterN ]
# letterN ::= ( starting index, ending index )
def fst_pass(line):
	candidate = []
	word = []
	start_letter, end_letter = -1, -1
	wlist = []

	(height, length) = line.shape
	for i in range (0, length):
		sum = sumup_col(line, i)
		if sum > 0 and start_letter == -1:
			if i == 0:
				start_letter = i
			else:
				start_letter = i - 1
			if start_letter - end_letter > 5:
				if word != []:
					candidate.append(word)
					word = []
		elif sum > 0 or (sum == 0 and start_letter == -1):
			continue
		elif sum == 0:
			end_letter = i
			width = end_letter - start_letter
			wlist.append(width)
			word.append((start_letter, end_letter))
			start_letter = -1

	if start_letter != -1:
		width = length - 1 - start_letter
		wlist.append(width)
		word.append((start_letter, length - 1))
	if word != []:
		candidate.append(word)
	return (statistics.median(wlist), candidate)

# Calculates the difference of end and start pts of each letter, returns a list of widths
def calc_width(word):
	width = []
	for i in word:
		width.append(i[1] - i[0])
	return width

def find_split_pts(index, num_letter, size, img):
	(_, w) = img.shape
	i = 0
	pts = []
	while num_letter != 0:
		pt, m = -1, float("inf")
		for j in range (i + int(size), min(w, i + int(size) + 7)):
			s = sumup_col(img, j)
			if (s <= m):
				pt = j
				m = s
		if pt == -1:
			pt = w - 1
		pts.append((index + i, index + pt))
		i = pt
		num_letter = num_letter - 1
	return pts

# Merges and splits letters considering the context
# Return value:
#		[ word1, word2, word3, ... , wordN ]
# wordN ::= [ letter1, letter2, ... , letterN ]
# letterN ::= ( starting index, ending index )
def snd_pass(line, size, candidate):
	snd_candidate = []
	(height, _) = line.shape
	for word in candidate:
		snd_word = []
		width = calc_width(word)
		length = len(width)
		merged = 0
		for i in range (0, length - 1):
			if merged == 1:
				merged = 0
				continue
			if size - 5 <= word[i + 1][1] - word[i][0] < height and width[i] >= width[i + 1]:
				snd_word.append((word[i][0], word[i + 1][1]))
				merged = 1
			elif size - 2 <= width[i] < height:
				snd_word.append(word[i])
			elif width[i] >= height:
				num_letter = width[i] // size
				pts = find_split_pts(word[i][0], num_letter, size, line[0:, word[i][0]:word[i][1]])
				l = len(pts)
				for j in range (0, l):
					snd_word.append(pts[j])
					if j == l - 1:
						if word[i][1] - pts[j][1] <= size - 2:
							snd_word.append((pts[j][1], word[i + 1][1]))	
							merged = 1
						else:
							snd_word.append((pts[j][1], word[i][1]))
			else:
				snd_word.append(word[i])
		if merged == 0:
			snd_word.append(word[length - 1])
		snd_candidate.append(snd_word)
		snd_word = []
	return snd_candidate

# Reshape narrow letters to 32 X 32
# without modifying ratio
def reshape_with_margin(img, size=32, pad=4):
	if img.shape[0] > img.shape[1] :
		dim = img.shape[0]
		margin = (dim - img.shape[1])//2
		margin_img = np.zeros([dim, margin])
		reshaped = np.c_[margin_img, img, margin_img]
	else :
		dim = img.shape[1]
		margin = (dim - img.shape[0])//2
		margin_img = np.zeros([margin, dim])
		reshaped = np.r_[margin_img, img, margin_img]
	reshaped = cv2.resize(reshaped, (size-pad*2, size-pad*2))
	padded = np.zeros([size, size])
	padded[pad:-pad, pad:-pad] = reshaped
	return padded

# Given a paragraph, processes 2 times and returns the candidate word points
def proc_paragraph(para):
	fst_candidate = []
	snd_candidate = []
	wlist = []
	for line in para:
		(m, c) = fst_pass(line)
		fst_candidate.append(c)
		wlist.append(m)
	l = len(para)
	if len(wlist) == 0:
		return []
	letter_size = statistics.median(wlist)
	for i in range (0, l):
		c = snd_pass(para[i], letter_size, fst_candidate[i])
		snd_candidate.append(c)
	return snd_candidate

# Implemented for testing; truncates line image to letters and saves letter images
# with word and letter information
def trunc_n_save_letter(para_num, line_num, line, candidate):
	cnt_word = 0
	for word in candidate:
		cnt_letter = 0
		for letter in word:
			cv2.imwrite('test/char_testing/p' + str(para_num) + 'l' + str(line_num) +
					'w' + str(cnt_word) + 'l' + str(cnt_letter) + '.png', line[:,letter[0]:letter[1]])
			cnt_letter = cnt_letter + 1
		cnt_word = cnt_word + 1

# Implemented for testing; Given an essay, processes 2 times and saves letters as images
def save_essay(essay):
	l = len(essay)
	for i in range (0, l):
		c = proc_paragraph(essay[i])
		l2 = len(essay[i])
		for j in range (0, l2):
			trunc_n_save_letter(i, j, essay[i][j], c[j])

# Truncates line image to letters and constructs line classes
# Resizes char images to 32 * 32
def to_line(line, candidate):
	l = []
	length = len(candidate)
	for i in range (0, length):
		for letter in candidate[i]:
			img = reshape_with_margin(line[:,letter[0]:letter[1]])
			char = Char(img, CHARTYPE.CHAR)
			l.append(char)
		if i != length - 1:
			l.append(Char(None, CHARTYPE.BLANK))
	return Line(l)

# Given a paragraph image, constructs a paragraph class
def to_paragraph(para):
	l = []
	c = proc_paragraph(para)
	length = len(para)
	for i in range (0, length):
		line = to_line(para[i], c[i])	
		l.append(line)
	return Paragraph(l)

# reconst 모듈로 넘겨줄 paragraph list를 생성
def get_graphs(img):
	essay = dl.output_line_imgs(img)
	l = []
	length = len(essay)
	for i in range (0, length):
		para = to_paragraph(essay[i])
		l.append(para)
	return l

if __name__ == "__main__":
	run_direct()
