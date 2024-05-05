import * as services from './services.js';

/**
 * Configura um lançamento com as propriedades de categoria, subcategoria, conta e cartão.
 * 
 * @param {Object} transaction - Um objeto que representa um lançamento a ser configurada.
 * @returns {Promise<Object>} Uma promessa que resolve para o lançamento configurada.
 */
export async function setTransaction(transaction) {
    transaction.category = await setCategory(transaction.category);
    transaction.subcategory = await setSubcategory(transaction.subcategory);
    
    if (transaction.account) {
        transaction.account = await setAccount(transaction.account);
    }

    if (transaction.card) {
        transaction.card = await setCard(transaction.card);
    }

    return transaction;
}

/**
 * Configura uma conta com base em um ID de conta fornecido.
 * 
 * @param {string} accountId - O ID da conta a ser configurada.
 * @returns {Promise<Object>} Uma promessa que resolve para a conta configurada.
 */
export async function setAccount(accountId) {
    const banks = await services.getResource('banks'),
        accounts = await services.getResource('accounts');

    for (const account of accounts) {
        if (account.id == accountId) {
            for (const bank of banks) {
                if (bank.id == account.bank) {
                    account.bank = bank;
                    return account;
                }
            }
        }
    }
}

/**
 * Configura um cartão com base em um ID de cartão fornecido.
 * 
 * @param {string} cardId - O ID do cartão a ser configurado.
 * @returns {Promise<Object>} Uma promessa que resolve para o cartão configurado.
 */
export async function setCard(cardId) {
    const cards = await services.getResource('cards');

    for (const card of cards) {
        if (card.id == cardId) {
            return card;
        }
    }
}

/**
 * Configura uma categoria com base em um ID de categoria fornecido.
 * 
 * @param {string} categoryId - O ID da categoria a ser configurada.
 * @returns {Promise<Object>} Uma promessa que resolve para a categoria configurada.
 */
export async function setCategory(categoryId) {
    const categories = JSON.parse(sessionStorage.getItem('categories'));

    for (const category of categories) {
        if (category.id == categoryId) {
            return category;
        }
    }
}

/**
 * Configura uma subcategoria com base em um ID de subcategoria fornecido.
 * 
 * @param {string} subcategoryId - O ID da subcategoria a ser configurada.
 * @returns {Promise<Object>} Uma promessa que resolve para a subcategoria configurada.
 */
export async function setSubcategory(subcategoryId) {
    const subcategories = await services.getResource('subcategories');

    for (const subcategory of subcategories) {
        if (subcategory.id == subcategoryId) {
            return subcategory;
        }
    }
}
