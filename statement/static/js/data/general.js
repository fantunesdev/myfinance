/**
 * Remove todos os acentos de uma string, transformando-a em sua versão sem acentos.
 * 
 * @param {string} str - A string de entrada que pode conter caracteres acentuados.
 * @returns {string} A string de entrada com todos os acentos removidos.
 */
export function removeAccents(str) {
    return str.normalize('NFD').replace(/[\u0300-\u036f]/g, '');
}

/**
 * Substitui todos os espaços em branco de uma string por underscores.
 * 
 * @param {string} str - A string de entrada que pode conter espaços em branco.
 * @returns {string} A string de entrada com todos os espaços em branco substituídos por underscores.
 */
export function removeSpaces(str) {
    return str.replace(/\s/g, '_');
}

/**
 * Trata uma string para adequá-la ao uso como identificador em um sistema,
 * removendo espaços, acentos e convertendo todos os caracteres para minúsculas.
 * 
 * @param {string} str - A string de entrada que pode conter espaços, acentos e letras maiúsculas.
 * @returns {string} A string tratada, sem espaços, sem acentos e em letras minúsculas.
 */
export function handleNamesToComputer(str) {
    const strWithoutSpaces = removeSpaces(str);
    const strWithoutAccents = removeAccents(strWithoutSpaces);
    return strWithoutAccents.toLowerCase();
}

/**
 * Converte um número de ponto flutuante para uma string com duas casas decimais
 * e substitui o ponto (`.`) por vírgula (`,`), conforme a convenção de formatação de números em alguns países.
 * 
 * @param {number} float - O número de ponto flutuante a ser formatado.
 * @returns {string} O número formatado com duas casas decimais e ponto (`.`) substituído por vírgula (`,`).
 */
export function handleCurrency(float) {
    const str = String(float.toFixed(2));
    return str.replace('.', ',');
}
