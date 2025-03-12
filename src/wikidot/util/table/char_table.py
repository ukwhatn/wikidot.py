# 特殊記号・非英語アルファベットを英語アルファベットに変換する
special_char_map = {
    "À": "a",
    "Á": "a",
    "Â": "a",
    "Ã": "a",
    "Ä": "ae",
    "Å": "a",
    "Æ": "ae",
    "Ç": "c",
    "È": "e",
    "É": "e",
    "Ê": "e",
    "Ë": "e",
    "Ì": "i",
    "Í": "i",
    "Î": "i",
    "Ï": "i",
    "Ð": "d",
    "Ñ": "n",
    "Ò": "o",
    "Ó": "o",
    "Ô": "o",
    "Õ": "o",
    "Ö": "oe",
    "Ø": "o",
    "Ù": "u",
    "Ú": "u",
    "Û": "u",
    "Ü": "ue",
    "Ý": "y",
    "Þ": "t",
    "ß": "ss",
    "à": "a",
    "á": "a",
    "â": "a",
    "ã": "a",
    "ä": "ae",
    "å": "a",
    "æ": "ae",
    "ç": "c",
    "è": "e",
    "é": "e",
    "ê": "e",
    "ë": "e",
    "ì": "i",
    "í": "i",
    "î": "i",
    "ï": "i",
    "ð": "d",
    "ñ": "n",
    "ò": "o",
    "ó": "o",
    "ô": "o",
    "õ": "o",
    "ö": "oe",
    "ø": "o",
    "ù": "u",
    "ú": "u",
    "û": "u",
    "ü": "ue",
    "ý": "y",
    "þ": "t",
    "ÿ": "y",
    "Ā": "a",
    "ā": "a",
    "Ă": "a",
    "ă": "a",
    "Ą": "a",
    "ą": "a",
    "Ć": "c",
    "ć": "c",
    "Ĉ": "c",
    "ĉ": "c",
    "Ċ": "c",
    "ċ": "c",
    "Č": "c",
    "č": "c",
    "Ď": "d",
    "ď": "d",
    "Đ": "d",
    "đ": "d",
    "Ē": "e",
    "ē": "e",
    "Ĕ": "e",
    "ĕ": "e",
    "Ė": "e",
    "ė": "e",
    "Ę": "e",
    "ę": "e",
    "Ě": "e",
    "ě": "e",
    "Ĝ": "g",
    "ĝ": "g",
    "Ğ": "g",
    "ğ": "g",
    "Ġ": "g",
    "ġ": "g",
    "Ģ": "g",
    "ģ": "g",
    "Ĥ": "h",
    "ĥ": "h",
    "Ħ": "h",
    "ħ": "h",
    "Ĩ": "i",
    "ĩ": "i",
    "Ī": "i",
    "ī": "i",
    "Ĭ": "i",
    "ĭ": "i",
    "Į": "i",
    "į": "i",
    "İ": "i",
    "ı": "i",
    "Ĳ": "ij",
    "ĳ": "ij",
    "Ĵ": "j",
    "ĵ": "j",
    "Ķ": "k",
    "ķ": "k",
    "ĸ": "k",
    "Ĺ": "l",
    "ĺ": "l",
    "Ļ": "l",
    "ļ": "l",
    "Ľ": "l",
    "ľ": "l",
    "Ŀ": "l",
    "ŀ": "l",
    "Ł": "l",
    "ł": "l",
    "Ń": "n",
    "ń": "n",
    "Ņ": "n",
    "ņ": "n",
    "Ň": "n",
    "ň": "n",
    "ŉ": "n",
    "Ŋ": "n",
    "ŋ": "n",
    "Ō": "o",
    "ō": "o",
    "Ŏ": "o",
    "ŏ": "o",
    "Ő": "o",
    "ő": "o",
    "Œ": "oe",
    "œ": "oe",
    "Ŕ": "r",
    "ŕ": "r",
    "Ŗ": "r",
    "ŗ": "r",
    "Ř": "r",
    "ř": "r",
    "Ś": "s",
    "ś": "s",
    "Ŝ": "s",
    "ŝ": "s",
    "Ş": "s",
    "ş": "s",
    "Š": "s",
    "š": "s",
    "Ţ": "t",
    "ţ": "t",
    "Ť": "t",
    "ť": "t",
    "Ŧ": "t",
    "ŧ": "t",
    "Ũ": "u",
    "ũ": "u",
    "Ū": "u",
    "ū": "u",
    "Ŭ": "u",
    "ŭ": "u",
    "Ů": "u",
    "ů": "u",
    "Ű": "u",
    "ű": "u",
    "Ų": "u",
    "ų": "u",
    "Ŵ": "w",
    "ŵ": "w",
    "Ŷ": "y",
    "ŷ": "y",
    "Ÿ": "y",
    "Ź": "z",
    "ź": "z",
    "Ż": "z",
    "ż": "z",
    "Ž": "z",
    "ž": "z",
    "ſ": "ss",
    "Ƒ": "f",
    "ƒ": "f",
    "Ș": "s",
    "ș": "s",
    "Ț": "t",
    "ț": "t",
    "Ά": "a",
    "Έ": "e",
    "Ή": "i",
    "Ί": "i",
    "Ό": "o",
    "Ύ": "y",
    "Ώ": "o",
    "ΐ": "i",
    "Α": "a",
    "Β": "v",
    "Γ": "g",
    "Δ": "d",
    "Ε": "e",
    "Ζ": "z",
    "Η": "i",
    "Θ": "th",
    "Ι": "i",
    "Κ": "k",
    "Λ": "l",
    "Μ": "m",
    "Ν": "n",
    "Ξ": "x",
    "Ο": "o",
    "Π": "p",
    "Ρ": "r",
    "Σ": "s",
    "Τ": "t",
    "Υ": "y",
    "Φ": "f",
    "Χ": "ch",
    "Ψ": "ps",
    "Ω": "o",
    "Ϊ": "i",
    "Ϋ": "y",
    "ά": "a",
    "έ": "e",
    "ή": "i",
    "ί": "i",
    "ΰ": "y",
    "α": "a",
    "β": "v",
    "γ": "g",
    "δ": "d",
    "ε": "e",
    "ζ": "z",
    "η": "i",
    "θ": "th",
    "ι": "i",
    "κ": "k",
    "λ": "l",
    "μ": "m",
    "ν": "n",
    "ξ": "x",
    "ο": "o",
    "π": "p",
    "ρ": "r",
    "ς": "s",
    "σ": "s",
    "τ": "t",
    "υ": "y",
    "φ": "f",
    "χ": "ch",
    "ψ": "ps",
    "ω": "o",
    "ϊ": "i",
    "ϋ": "y",
    "ό": "o",
    "ύ": "y",
    "ώ": "o",
    "ϴ": "th",
    "Ё": "e",
    "Ђ": "d",
    "Ѓ": "g",
    "Є": "e",
    "Ѕ": "z",
    "І": "i",
    "Ї": "i",
    "Ј": "j",
    "Љ": "l",
    "Њ": "n",
    "Ћ": "c",
    "Ќ": "k",
    "Ў": "u",
    "Џ": "d",
    "А": "a",
    "Б": "b",
    "В": "v",
    "Г": "g",
    "Д": "d",
    "Е": "e",
    "Ж": "z",
    "З": "z",
    "И": "i",
    "Й": "j",
    "К": "k",
    "Л": "l",
    "М": "m",
    "Н": "n",
    "О": "o",
    "П": "p",
    "Р": "r",
    "С": "s",
    "Т": "t",
    "У": "u",
    "Ф": "f",
    "Х": "h",
    "Ц": "c",
    "Ч": "c",
    "Ш": "s",
    "Щ": "s",
    "Ы": "y",
    "Э": "e",
    "Ю": "u",
    "Я": "a",
    "а": "a",
    "б": "b",
    "в": "v",
    "г": "g",
    "д": "d",
    "е": "e",
    "ж": "z",
    "з": "z",
    "и": "i",
    "й": "j",
    "к": "k",
    "л": "l",
    "м": "m",
    "н": "n",
    "о": "o",
    "п": "p",
    "р": "r",
    "с": "s",
    "т": "t",
    "у": "u",
    "ф": "f",
    "х": "h",
    "ц": "c",
    "ч": "c",
    "ш": "s",
    "щ": "s",
    "ы": "y",
    "э": "e",
    "ю": "u",
    "я": "a",
    "ё": "e",
    "ђ": "d",
    "ѓ": "g",
    "є": "e",
    "ѕ": "z",
    "і": "i",
    "ї": "i",
    "ј": "j",
    "љ": "l",
    "њ": "n",
    "ћ": "c",
    "ќ": "k",
    "ў": "u",
    "џ": "d",
    "Ѣ": "e",
    "ѣ": "e",
    "Ѫ": "a",
    "ѫ": "a",
    "Ѳ": "f",
    "ѳ": "f",
    "Ѵ": "y",
    "ѵ": "y",
    "Ґ": "g",
    "ґ": "g",
    "Ғ": "g",
    "ғ": "g",
    "Ҕ": "g",
    "ҕ": "g",
    "Җ": "z",
    "җ": "z",
    "Қ": "k",
    "қ": "k",
    "Ҝ": "k",
    "ҝ": "k",
    "Ҟ": "k",
    "ҟ": "k",
    "Ҡ": "k",
    "ҡ": "k",
    "Ң": "n",
    "ң": "n",
    "Ҥ": "n",
    "ҥ": "n",
    "Ҧ": "p",
    "ҧ": "p",
    "Ҩ": "o",
    "ҩ": "o",
    "Ҫ": "s",
    "ҫ": "s",
    "Ҭ": "t",
    "ҭ": "t",
    "Ү": "u",
    "ү": "u",
    "Ұ": "u",
    "ұ": "u",
    "Ҳ": "h",
    "ҳ": "h",
    "Ҵ": "c",
    "ҵ": "c",
    "Ҷ": "c",
    "ҷ": "c",
    "Ҹ": "c",
    "ҹ": "c",
    "Һ": "h",
    "һ": "h",
    "Ҽ": "c",
    "ҽ": "c",
    "Ҿ": "c",
    "ҿ": "c",
    "Ӂ": "z",
    "ӂ": "z",
    "Ӄ": "k",
    "ӄ": "k",
    "Ӆ": "l",
    "ӆ": "l",
    "Ӈ": "n",
    "ӈ": "n",
    "Ӊ": "n",
    "ӊ": "n",
    "Ӌ": "c",
    "ӌ": "c",
    "Ӑ": "a",
    "ӑ": "a",
    "Ӓ": "a",
    "ӓ": "a",
    "Ӕ": "ae",
    "ӕ": "ae",
    "Ӗ": "e",
    "ӗ": "e",
    "Ә": "a",
    "ә": "a",
    "Ӛ": "a",
    "ӛ": "a",
    "Ӝ": "z",
    "ӝ": "z",
    "Ӟ": "z",
    "ӟ": "z",
    "Ӡ": "z",
    "ӡ": "z",
    "Ӣ": "i",
    "ӣ": "i",
    "Ӥ": "i",
    "ӥ": "i",
    "Ӧ": "o",
    "ӧ": "o",
    "Ө": "o",
    "ө": "o",
    "Ӫ": "o",
    "ӫ": "o",
    "Ӯ": "u",
    "ӯ": "u",
    "Ӱ": "u",
    "ӱ": "u",
    "Ӳ": "u",
    "ӳ": "u",
    "Ӵ": "c",
    "ӵ": "c",
    "Ӹ": "y",
    "ӹ": "y",
    "Ԋ": "n",
    "ԋ": "n",
    "Ԏ": "t",
    "ԏ": "t",
    "Ԛ": "q",
    "ԛ": "q",
    "Ԝ": "w",
    "ԝ": "w",
}
