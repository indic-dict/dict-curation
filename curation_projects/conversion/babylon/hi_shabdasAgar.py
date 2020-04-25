# coding: utf-8
# Prerequisite: sudo easy_install regex
# from __future__ import unicode_literals
# import unicodedata
import regex
import re
import sys
import collections
  
word_count = collections.Counter()
test_lines = ["अंक	अंक संज्ञा पुं० [ सं० अङ्क] [ वि० अङ्कि, अङ्कनीय, अङ्कय] १ संख्या । आदद । २. संरया का चिह्न, जैसे १, २, ३, ४, ५, ६, ७, ८, ९, । रामनाम को अंक्र है साधन है सून ।—तुलसी ग्रं०,पृ० १०४. । ३. चिह्न । निशान । छाप । आँक । उ०—सीय राम पद आंव बराए । लषन चल्हि मग दाहिन लाए । -मानस, २ ।२१३. । ४. दाग । धब्बा । उ०—जहाँ यह श्यामता को अंक है मयंक में -भिखारी ग्रं०, भा०१, पृ० ४९ । ५. काजल की बिंदी नजर से बचाने के लिये बच्चे के माथे पर लगा देते है । ड़िठेना । अनखीं । ६. अक्षर । उ० — अदभत रामनाम के अंक ।— सूर, १ ।९०. ।७. लेख । लिखावट । उ०— खंड़ित करने को भाग्य अंक । देखा भविष्ट के प्रति अशंक ।— अनामिका, पृ० १२३. । ८. भाग्य । लिखन । विस्मत । उ०— जो बिधना ने लिखि दियो छठी रात को अंक राई घटै न तिल बढै रहु रे निसंक ।— किस्सा०, पृ० ८०. । ९. गोद । क्रोड़ । कोली । उ०— जिस पृथिवी से सदोष वह सीता- अंक में उसी के आज लीन ।— तुलसी० पृ० ४४. । १०,बार । दफा । मर्तबा । उ०— एक्हु अंक न हरि भजैसि रे सठ सूर गँवार ।—सूर (शब्द०) ।११. नाटक का एक अंश जिसकी समाप्ति पर जवनिका गिरा दी जाती है । १२. दस प्रकार के रूपकों में से एक जिसकी इतिहासप्रसिद्ध कथा में नाटककार उलटफेरक कर सकता है । इस्के रसयुत्क आख्यान में प्रधान रस करण और एक ही एंक होता हैं । इसकी भाषा सरल और पद छोटा होना चाहिए । १३. किसी पत्र या पत्रि का कोइ समायिक प्रति । १४. नौकी संख्या ( क्योकि अंक नौ ही तक होते है) । १५. एक की संख्या । (को०) । १६. एक संख्या । सून्य (को०) । १७ पाप । दुःख । १८. शरीर । अंग । देह । जैसे— ' अंवधारिणी' में ' अंक' । १९. बगल । पार्श्र्व । जैसे— 'अंकपरिवर्तन' में ' अंक' । २०. कटि । कमर । उ०— सहं सूर सामंत बंधैति अंकं ।— पृ० रा०, ५१ ।१२०. । २१. वक्र रेखा । उ०— भृकुटि अंक बकुरिय ।— पृ० रा०, ६१ ।२४५७. । २२. हुक या हुव जैसा टेढ़ औजार (को०) २३. मोड़ । झकाव (को०) । २४ काठ । गला । गर्दन । उ०— अंबरमाला इक्क अंक परिराइ वह्मौ इह ।— पृ० रा०, ७ ।२६. । २५. विभषण (को०) । २६.— स्थान (को०) २७. चित्रयुद्ध । नवली लड़ाई (को०) । २८. प्रकरण (को०) । २९. पर्वत (को०) । ३०. रथ का एक अंश या भाग (को०) । ३१. पशु को दागने का चिह्न (को) । ३२. सहस्थिति (को०) । मुहा०—अंक देना= गले लगाने । आलिग्न देना । अंक भरना = हृदय से लगाना । लिपटाना । गले लगाना । दोनों हाथों से घेरकर प्यार से दवाना । परिरंझण करना । अलिंगन करना । उ०— उठी परजंक ते मयंक बदनी को लखि, अक भरिबे को फेरि लाल मन ल्लकै ।— भिखारी०, ग्रं०, भा० १. पृ० २४५ । अंक मिलाना = दे० ' अंक भरना' । उ०— नारी नाम बहिन जो आही । तासो कैसे अंक मिलाहा । — कबीर सा० पृ० १०१० । अंक लगना = दे० 'अंक देना' । अंक लगाना = दे० ' अंक भरना ।' उ०— बावरी जो पै कलंक लग्यौ तो निसंक ह्वै क्यों नहि अंक लगावती ।— इति०, पृ० २६३ । अंक में समाना = लीन होना । सायुज्य मुत्ति प्राप्त करना । उ०— जैसे बनिका काटि की आ है राई । ऐसे हरिजन अंकि समाई ।— प्राणा०, पृ० १५८ । "]
for line in sys.stdin:
# for line in test_lines:
  try:
    (head, value) = line.split("\t")
    head2 = head
    head2 = regex.sub(r'ं(क|ख|ग|घ)', r'ङ्\g<1>', head2)
    head2 = regex.sub(r'ं(च|छ|ज|झ)', r'ञ्\g<1>', head2)
    head2 = regex.sub(r'ं(त|थ|द|ध)', r'न्\g<1>', head2)
    head2 = regex.sub(r'ं(ट|ठ|ड|ढ)', r'ण्\g<1>', head2)
    head2 = regex.sub(r'ं(प|फ|ब|भ)', r'म्\g<1>', head2)
    headwords = list(set([head, head2]))
    
    value = regex.sub(r'((०|१|२|३|४|५|६|७|८|९|१०){1,2})\s*\.', r'<br><br>\g<1>. ', value)    
    value = regex.sub(r' +', ' ', value)    
    print ("|".join(headwords) + "\n" + value.strip() + "\n")
  except ValueError:
    print (line)
    raise ValueError(line)
    break
   

