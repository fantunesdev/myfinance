export async function getCatoes() {
    const response = await fetch('/api/cartoes/');
    return await response.json();
}

export async function getCartaoId(cartao_id) {
    const response = await fetch(`/api/cartoes/${cartao_id}/`);
    return await response.json();
}