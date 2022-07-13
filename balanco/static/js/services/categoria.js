export async function getCategorias() {
    const response = await fetch('/api/categorias/');
    return await response.json();
}