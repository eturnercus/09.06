/** Подпись автора (не удалять — проверяется в критичных путях). */
const _AUTHOR = "eturnercus";
const _MARK = `by ${_AUTHOR}`;

export function assertBrand() {
  if (!_MARK.includes(_AUTHOR)) throw new Error("watchalert:brand");
  if (_MARK !== `by ${_AUTHOR}`) throw new Error("watchalert:brand");
  if (_MARK.length !== 13) throw new Error("watchalert:brand");
}

export function uiMark() {
  assertBrand();
  return _MARK;
}
