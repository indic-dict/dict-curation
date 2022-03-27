import re
from collections import OrderedDict

from indic_transliteration.sanscript import transliterate, DEVANAGARI, ITRANS
from lxml import etree
from lxml.etree import Element


NIGHANTU_NAAMA = "अभिधानमञ्जरी"


class AbhidaanamanjariiGanaVarga(object):

	def __init__(self, gana_varga_sankhya, gana_varga_naama):
		super(AbhidaanamanjariiGanaVarga, self).__init__()
		self.gana_varga_sankhya = gana_varga_sankhya
		self.gana_varga_naama = gana_varga_naama

		self.index = str(gana_varga_sankhya)
		self.vargas = []
		self.prarambha_shloka = None

	@classmethod
	def from_h1_elem(cls, gana_varga_sankhya, h1_elem, parent_node):
		"""

		:param gana_varga_sankhya:
		:type h1_elem: Element
		:param parent_node:
		:return:
		"""
		print("26: ", gana_varga_sankhya, etree.tounicode(h1_elem))
		gana_varga_naama = h1_elem.xpath('span[@class="mw-headline"]')[0].text
		gana_varga = cls(gana_varga_sankhya, gana_varga_naama)
		gana_varga.vargas.extend(
			cls.get_vargas(gana_varga, h1_elem, parent_node))
		if not len(gana_varga.vargas):
			node_index = parent_node.index(h1_elem)
			next_node = parent_node[node_index + 1]
			if next_node.tag == 'div' and next_node.get('class') == 'poem':
				content_p = next_node.xpath('big/center/p')[0]
				ps, next_index = AbhidaanamanjariiShloka.aggregate_next_shloka(content_p, 0)
				if ps:
					gana_varga.prarambha_shloka = ps
					gana_varga.prarambha_shloka.shloka_html = content_p.text.strip().replace('||', '॥').replace('|', '।') + '</br>' + gana_varga.prarambha_shloka.shloka_html
		return gana_varga

	@classmethod
	def get_vargas(cls, gana_varga, h1_elem, parent_node):
		vargas = []
		node_index = parent_node.index(h1_elem)
		varga_sankhya = 0
		while True:
			varga_sankhya = varga_sankhya + 1
			node_index = node_index + 1

			if len(parent_node) <= node_index:
				break
			current_node = parent_node[node_index]  # type: Element
			if current_node.tag != 'h2':
				break

			print("48,", current_node.tag)
			varga = AbhidhaanamanjariiVarga.from_h2_elem(
				gana_varga, varga_sankhya, current_node, parent_node)
			if varga.anukramanika or varga.upasamhara or varga.pushpika or len(varga.dhaatus):
				node_index+= 1
			if varga is not None:
				vargas.append(varga)
		return vargas

	def get_headers(self):
		return [
			self.gana_varga_naama,
			NIGHANTU_NAAMA + " - _" + self.index,
			transliterate(self.gana_varga_naama, DEVANAGARI, ITRANS),
			transliterate(NIGHANTU_NAAMA + " - _" + self.index, DEVANAGARI, ITRANS)
		]

	def get_content(self, pr_gv_naama, nx_gv_naama):
		content = ''
		if self.prarambha_shloka:
			content+= self.prarambha_shloka.get_content()
			content+= "</br>"

		if len(self.vargas):
			varga_list = ''
			for varga in self.vargas:
				varga_list+= """
					<dt>
						{index}. <a href="{varga_naama}">{varga_naama}</a>
					</dt>
				""".format(index=varga.index, varga_naama=varga.varga_naama)
			content+= '<dl>{}</dl>'.format(varga_list)

		navigation_content =  '┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈</br><a href="{pr}">{pr}</a> ⬸ • ⤑ <a href="{nx}">{nx}</a>'.format(pr=pr_gv_naama, nx=nx_gv_naama)
		content+= navigation_content

		return content


class AbhidhaanamanjariiVarga(object):

	def __init__(self, gana_varga, varga_sankhya, varga_naama):
		super(AbhidhaanamanjariiVarga, self).__init__()
		self.gana_varga = gana_varga
		self.varga_sankhya = varga_sankhya
		self.varga_naama = varga_naama
		
		self.index = '.'.join([str(gana_varga.gana_varga_sankhya), str(varga_sankhya).rjust(2, '0')])
		self.anukramanika = None
		self.upasamhara = None
		self.pushpika = None
		self.dhaatus = []

	def set_anukramanika(self, anukramanika):
		self.anukramanika = anukramanika

	def set_upasamhara(self, upsamhara):
		self.upasamhara = upsamhara

	def set_pushpika(self, pushpika):
		self.pushpika = pushpika

	def get_headers(self):
		return [
			self.varga_naama,
			NIGHANTU_NAAMA + ' _' + transliterate(self.index, ITRANS, DEVANAGARI),
			transliterate(self.varga_naama, DEVANAGARI, ITRANS),
			transliterate(NIGHANTU_NAAMA, DEVANAGARI, ITRANS) + ' _' + self.index,
			'abdm _' + self.index
		]

	def get_content(self, pr_varga_naama, nx_varga_naama):
		content = ''
		hierarchy = '<code><small><a href="{h1}">{h1}</a> » <span>{h2}</span></small></code></br>'.format(h1=self.gana_varga.gana_varga_naama, h2=self.varga_naama)
		content+= hierarchy
		if self.anukramanika:
			content+= '<b>{}</b>'.format(self.anukramanika.dhaatu_naama)
			for shloka in self.anukramanika.shlokas:
				content+= shloka.get_content()
		dhaatu_index = ''
		for dhaatu in self.dhaatus:
			dhaatu_index+= '<a href="{dhaatu_naama}">{dhaatu_naama}</a>, '.format(dhaatu_naama=dhaatu.dhaatu_naama)
		content+= '<p>{}</p>'.format(dhaatu_index)
		if self.upasamhara:
			content += '<b>{}</b>'.format(self.upasamhara.dhaatu_naama)
			for shloka in self.upasamhara.shlokas:
				content += shloka.get_content()
		if self.pushpika:
			content += '<b>{}</b>'.format(self.pushpika.dhaatu_naama)
			for shloka in self.pushpika.shlokas:
				content += shloka.get_content()
		navigation_content = '┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈</br><a href="{pr}">{pr}</a> ⬸ • ⤑ <a href="{nx}">{nx}</a>'.format(pr=pr_varga_naama, nx=nx_varga_naama)
		content+= navigation_content
		return content

	@classmethod
	def from_h2_elem(cls, gana_varga, varga_sankhya, h2_elem, parent_node):
		print("86: ", gana_varga, varga_sankhya, h2_elem.tag, etree.tounicode(h2_elem))
		varga_naama = h2_elem.xpath('span[@class="mw-headline"]')[0].text
		varga = cls(gana_varga, varga_sankhya, varga_naama)
		dhaatus = cls.get_dhaatus(varga, h2_elem, parent_node)
		for dhaatu in dhaatus:
			if dhaatu.dhaatu_naama == "अनुक्रमणिका":
				varga.set_anukramanika(dhaatu)
			elif dhaatu.dhaatu_naama == "उपसंहार":
				varga.set_upasamhara(dhaatu)
			elif dhaatu.dhaatu_naama == "पुष्पिका":
				varga.set_pushpika(dhaatu)
			else:
				varga.dhaatus.append(dhaatu)
		return varga

	@classmethod
	def get_dhaatus(cls, varga, h2_elem, parent_node):
		h2_elem_index = parent_node.index(h2_elem)
		poem_div_index = h2_elem_index + 1
		if poem_div_index >= len(parent_node):
			return []

		poem_div = parent_node[poem_div_index]
		content_ps = poem_div.xpath('big/center/p')
		if not len(content_ps):
			return []

		return cls.get_dhaatus_from_content(varga, content_ps[0])


	@classmethod
	def get_dhaatus_from_content(cls, varga, content_p):
		dhaatu_naama_nodes = content_p.xpath('b')
		return [
			AbhidaanamanjariiDhaatu.from_dhaatu_elem(
				varga, iv[0], iv[1], content_p
			) for iv in enumerate(dhaatu_naama_nodes)
		]


class AbhidaanamanjariiDhaatu(object):

	def __init__(self, varga, dhaatu_sankhya, dhaatu_naama):
		super(AbhidaanamanjariiDhaatu, self).__init__()
		self.varga = varga
		self.dhaatu_sankhya = dhaatu_sankhya
		self.dhaatu_naama = dhaatu_naama

		self.index = '.'.join([
			str(varga.gana_varga.gana_varga_sankhya),
			str(varga.varga_sankhya).rjust(2, '0'),
			str(dhaatu_sankhya).rjust(3, '0')
		])
		self.shlokas = []

	def get_headers(self):
		dhaatu_headers = [
			self.dhaatu_naama,
			NIGHANTU_NAAMA + ' _' + transliterate(self.index, ITRANS, DEVANAGARI),
			transliterate(self.dhaatu_naama, DEVANAGARI, ITRANS),
			transliterate(NIGHANTU_NAAMA, DEVANAGARI, ITRANS) + ' _' + self.index,
			'abdm _' + self.index
		]
		for shloka in self.shlokas:
			shloka_headers = shloka.get_headers()
			if shloka_headers is None:
				continue
			dhaatu_headers.extend(shloka_headers)
		return dhaatu_headers

	def get_content(self, previous_dhaatu_naama, next_dhaatu_naama):
		hierarchy = '<code><small><a href="{h1}">{h1}</a> » <a href="{h2}">{h2}</a> » <span>{h3}</span></small></code></br>'.format(h1=self.varga.gana_varga.gana_varga_naama, h2=self.varga.varga_naama, h3=self.dhaatu_naama)
		dhatu_content = ''.join([s.get_content() for s in self.shlokas])
		navigation_content = '┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈</br><a href="{pr}">{pr}</a> ⬸ • ⤑ <a href="{nx}">{nx}</a>'.format(pr=previous_dhaatu_naama, nx=next_dhaatu_naama)
		return hierarchy + dhatu_content + navigation_content

	@classmethod
	def from_dhaatu_elem(cls, varga, dhaatu_sankhya, dhaatu_elem, content_p):
		dhaatu_naama = dhaatu_elem.text.strip()
		dhaatu = cls(varga, dhaatu_sankhya, dhaatu_naama)
		shlokas = cls.get_shlokas(dhaatu, dhaatu_elem, content_p)
		dhaatu.shlokas.extend(shlokas)
		return dhaatu

	@classmethod
	def get_shlokas(cls, dhaatu, dhaatu_elem, content_p):
		current_index = content_p.index(dhaatu_elem) + 1
		shlokas = []
		while True:
			shloka, current_index = AbhidaanamanjariiShloka.aggregate_next_shloka(content_p, current_index)
			if shloka is None:
				break
			shlokas.append(shloka)
		return shlokas



class AbhidaanamanjariiShloka(object):

	def __init__(self):
		super(AbhidaanamanjariiShloka, self).__init__()
		self.shloka_sankhya = None
		self.shloka_html = None

	def set_shloka_sankhya(self, shloka_sankhya):
		self.shloka_sankhya = shloka_sankhya.rjust(3, '०')

	def set_shloka_html(self, shloka_html):
		self.shloka_html = shloka_html

	@classmethod
	def aggregate_next_shloka(cls, content_p, current_index):

		shloka = cls()
		shloka.set_shloka_html('')

		while True:
			if current_index >= len(content_p):
				if shloka.shloka_html:
					return shloka, current_index
				return None, current_index
			current_node = content_p[current_index]
			if current_node.tag != 'br':
				print(shloka.shloka_html, 'is none')
				if shloka.shloka_html:
					return shloka, current_index
				else:
					return None, current_index
			br_string = str(current_node.tail).strip().replace('||', '॥').replace('|', '।')
			if not br_string:
				if shloka.shloka_html:
					return shloka, current_index
				return None, current_index + 1

			shloka.shloka_html+= br_string + '</br>'
			shloka_sankhya_match = re.match(r'^.*[।॥](?P<sankhya>[०-९]+)[।॥] *$', br_string)
			if shloka_sankhya_match:
				shloka.set_shloka_sankhya(shloka_sankhya_match.group('sankhya'))
				return shloka, current_index + 1

			current_index+= 1

	def get_content(self):
		if not self.shloka_html:
			return None
		return '<figure>{}</figure>'.format(self.shloka_html)

	def get_headers(self):
		if not self.shloka_sankhya:
			return []
		shloka_sankhya_it = transliterate(self.shloka_sankhya, DEVANAGARI, ITRANS)
		return [
			NIGHANTU_NAAMA + ' ' + self.shloka_sankhya,
			transliterate(NIGHANTU_NAAMA, DEVANAGARI, ITRANS) + ' ' + shloka_sankhya_it,
			'abdm {}'.format(shloka_sankhya_it)
		]


def create_root_index(gana_vargas):
	content = ''
	gana_varga_list = ''
	for i, gv in enumerate(gana_vargas):
		gana_varga_list+= '<dt>{index}. <a href="{gana_varga_naama}">{gana_varga_naama}</a></dt>'.format(index=transliterate(gv.index, ITRANS, DEVANAGARI), gana_varga_naama=gv.gana_varga_naama)
		varga_list = ''
		for v in gv.vargas:
			varga_list+= '<dt>{index}. <a href="{varga_naama}">{varga_naama}</a></dt>'.format(index=transliterate(v.index, ITRANS, DEVANAGARI), varga_naama=v.varga_naama)
		gana_varga_list+= '<dd><dl>{}</dl></dd>'.format(varga_list)
	content = '<dl>{}</dl>'.format(gana_varga_list)
	return content


def create_babylon(source_file_path, target_file_path):
	source_content = open(source_file_path, 'rb').read().decode('utf-8')
	target_file = open(target_file_path, 'ab')
	babylon_directives = OrderedDict([
		("stripmethod", "keep"),
		("sametypesequence", "h"),
		("bookname", NIGHANTU_NAAMA)
	])
	target_file.write('\n'.encode('utf-8'))
	for key, val in babylon_directives.items():
		directive_line = "#{key}={val}\n".format(key=key, val=val)
		target_file.write(directive_line.encode('utf-8'))
	target_file.write('\n'.encode('utf-8'))

	root = etree.fromstring(source_content)
	h1_elems = root.xpath('//h1')
	gana_vargas = [
		AbhidaanamanjariiGanaVarga.from_h1_elem(iv[0] + 1, iv[1], iv[1].getparent()) for iv in enumerate(h1_elems[1:])
	]
	index_headers = [NIGHANTU_NAAMA, transliterate(NIGHANTU_NAAMA, DEVANAGARI, ITRANS), 'abdm']
	index_content = create_root_index(gana_vargas).replace('\n', '')
	index_entry = '|'.join(index_headers) + '\n' + index_content + '\n\n'
	target_file.write(index_entry.encode('utf-8'))

	for i in range(0, len(gana_vargas)):
		gv = gana_vargas[i]
		pgv = ngv = None
		if i-1 >= 0:
			pgv = gana_vargas[i-1]
		if i+1 < len(gana_vargas):
			ngv = gana_vargas[i+1]
		gv_headers = gv.get_headers()
		gv_content = gv.get_content(pgv.gana_varga_naama if pgv else None, ngv.gana_varga_naama if ngv else None)
		gv_content = re.sub(r'[ \t][ \t]+', ' ', gv_content)
		gv_entry = '|'.join(gv_headers) + '\n' + gv_content.replace('\n', ' ') + '\n\n'
		target_file.write(gv_entry.encode('utf-8'))

		for j in range(0, len(gv.vargas)):
			v = gv.vargas[j]
			pv = nv = None
			if j - 1 >= 0:
				pv = gv.vargas[j - 1]
			if j + 1 < len(gv.vargas):
				nv = gv.vargas[j + 1]
			v_headers = v.get_headers()
			v_content = v.get_content(pv.varga_naama if pv else None, nv.varga_naama if nv else None)
			v_content = re.sub(r'[ \t][ \t]+', ' ', v_content)
			v_entry = '|'.join(v_headers) + '\n' + v_content.replace('\n', ' ') + '\n\n'
			target_file.write(v_entry.encode('utf-8'))

			for k in range(0, len(v.dhaatus)):
				d = v.dhaatus[k]
				pd = nd = None
				if k - 1 >= 0:
					pd = v.dhaatus[k - 1]
				if k + 1 < len(v.dhaatus):
					nd = v.dhaatus[k + 1]
				d_headers = d.get_headers()
				d_content = d.get_content(pd.dhaatu_naama if pd else None, nd.dhaatu_naama if nd else None)
				d_content = re.sub(r'[ \t][ \t]+', ' ', d_content)
				d_entry = '|'.join(d_headers) + '\n' + d_content.replace('\n', ' ') + '\n\n'
				target_file.write(d_entry.encode('utf-8'))


'''
from structures import *
source = open('source.html', 'rb').read().decode('utf-8')
root = etree.fromstring(source)

h1_elems = root.xpath('//h1')
gana_vargas = [
	AbhidaanamanjariiGanaVarga.from_h1_elem(iv[0] + 1, iv[1], iv[1].getparent()) for iv in enumerate(h1_elems[1:])
]

'''
