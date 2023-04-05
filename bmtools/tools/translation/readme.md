# Translation Queries

Contributor: [Shihao Liang](https://github.com/pooruss)

NLLB as translation tool:
- Language code should be included in queries in case the NLLB model cannot recognize the target language.
- Default source language is English. Change the nllb model path and source language in host_local_tools.py by passing a dict like this: {"model": ${your_nllb_path}, "src_lang": "eng_Latn"}
- Refer to paper [No Language Left Behind: Scaling Human-Centered Machine Translation](https://arxiv.org/abs/2207.04672) for all supported languages.

BAIDU translate api as translation tool:
- Set your APP ID and Secert Key in secret_keys.sh.
- Language code should also be included in queries.
- Refer to [Baidu translate](https://fanyi-api.baidu.com/product/11) for all supported languages.