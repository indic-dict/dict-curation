# coding: utf-8
# Prerequisite: sudo easy_install regex
import regex
import sys
import collections
  

word_count = collections.Counter()
test_lines = ["अघ अघ त् क तत्कृतौ . इति कविकल्पद्रुमः .. तत्-कृतिः पापकृर्तिः . अघयति व्याधः . कर्म्मणो-ऽर्थमध्यपाठादकर्म्मकोऽयं . तथा च	अघ अघ त् क तत्कृतौ . इति कविकल्पद्रुमः .. तत्-कृतिः पापकृर्तिः . अघयति व्याधः . कर्म्मणो-ऽर्थमध्यपाठादकर्म्मकोऽयं . तथा च, --“ धातोरर्थान्तरे वृत्ते धात्वर्थेनोपसङ्ग्रहात् .प्रसिद्धेरविवक्षातः कर्म्मणोऽकर्म्मिका क्रिया” ..इति गोयीचन्द्रः .. धात्वर्थेन सह कर्म्मण उप-सङ्ग्रहादित्यर्थः . क्रमेणोदाहरणानि . नदीवहति क्षरतीत्यर्थः . अघयति व्याधः . भवतिघटः . आहते जनः . इति दुर्गादासः .."]
for line in sys.stdin:
# for line in test_lines:
  headwords, value = line.split("\t&&\t")
  print headwords + "\n" + value.strip() + "\n"

