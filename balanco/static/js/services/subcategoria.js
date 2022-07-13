export async function getSubcategorias() {
    const response = await fetch('/api/subcategorias/');
    return await response.json();
}

export async function getSubcategoriasCategoria(categoria_id) {
    const response = await fetch(`/api/categorias/${categoria_id}/subcategorias/`);
    return await response.json();
}