(function() {
    const formPrefix = document.querySelector('[name$="-TOTAL_FORMS"]')?.name.split('-')[0] || 'cardnumber_set';
    let formCount = document.querySelectorAll(`[name="${formPrefix}-TOTAL_FORMS"]`);
    
    if (formCount.length === 0) {
        console.error('Formset management form não encontrado');
        return;
    }

    const totalFormsInput = formCount[0];
    const container = document.getElementById('card-numbers-container');
    const addButton = document.getElementById('add-card-number');

    if (!container || !addButton) {
        console.error('Container ou botão de adicionar não encontrado');
        return;
    }

    // Ensure management TOTAL_FORMS reflects actual rendered forms on load
    (function syncTotalForms() {
        try {
            const currentForms = container.querySelectorAll('.card-number-form').length;
            if (totalFormsInput) totalFormsInput.value = currentForms;
        } catch (e) {
            // ignore
        }
    })();

    // Extrai templates dos elementos vazios
    const emptyFormInput = document.querySelector('[data-empty-form-input]');
    const emptyFormHome = document.querySelector('[data-empty-form-home]');
    const emptyFormDependente = document.querySelector('[data-empty-form-dependente]');
    const emptyFormId = document.querySelector('[data-empty-form-id]');
    const emptyFormDelete = document.querySelector('[data-empty-form-delete]');
    const emptyFormName = document.querySelector('[data-empty-form-name]');

    // Função para formatar número do cartão
    function formatCardNumber(value) {
        // Remove caracteres não numéricos
        const cleaned = value.replace(/\D/g, '');
        // Limita a 16 dígitos
        const limited = cleaned.slice(0, 16);
        // Formata como xxxx xxxx xxxx xxxx
        const formatted = limited.replace(/(\d{4})(?=\d)/g, '$1 ');
        return formatted;
    }

    // Adiciona evento de formatação a um input
    function addFormatEventToInput(input) {
        if (input) {
            input.addEventListener('input', function(e) {
                // Pega o valor anterior e a posição do cursor
                const oldValue = this.value;
                const cursorPos = this.selectionStart;

                // Formata o novo valor
                const formatted = formatCardNumber(this.value);

                // Só atualiza se realmente mudou
                if (formatted !== oldValue) {
                    this.value = formatted;

                    // Calcula a nova posição do cursor
                    // Conta quantos dígitos tem antes da posição original
                    const beforeCursor = oldValue.substring(0, cursorPos).replace(/\D/g, '').length;

                    // Encontra onde esses dígitos terminam na string formatada
                    let digitCount = 0;
                    let newCursorPos = 0;
                    for (let i = 0; i < formatted.length; i++) {
                        if (formatted[i].match(/\d/)) {
                            digitCount++;
                            if (digitCount === beforeCursor + 1) {
                                newCursorPos = i + 1;
                                break;
                            }
                        }
                    }

                    // Se não encontrou (último dígito), coloca no final
                    if (newCursorPos === 0) {
                        newCursorPos = formatted.length;
                    }

                    this.setSelectionRange(newCursorPos, newCursorPos);
                }
            });
        }
    }

    function updateFormIndices() {
        const forms = container.querySelectorAll('.card-number-form');
        forms.forEach((form, index) => {
            form.dataset.formIndex = index;
            
            // Atualiza IDs e names de todos os campos
            const inputs = form.querySelectorAll('input, select, textarea');
            inputs.forEach(input => {
                const originalName = input.getAttribute('data-original-name') || input.name;
                const originalId = input.getAttribute('data-original-id') || input.id;
                
                if (originalName) {
                    input.name = originalName.replace(/__prefix__|_\d+_/g, `_${index}_`);
                }
                if (originalId) {
                    input.id = originalId.replace(/__prefix__|_\d+_/g, `_${index}_`);
                }
                
                // Armazena o nome original para próximas atualizações
                input.setAttribute('data-original-name', originalName);
                input.setAttribute('data-original-id', originalId);
            });

            // Atualiza labels
            const labels = form.querySelectorAll('label');
            labels.forEach(label => {
                const forAttr = label.getAttribute('for');
                if (forAttr) {
                    label.setAttribute('for', forAttr.replace(/__prefix__|_\d+_/g, `_${index}_`));
                }
            });
        });
    }

    function removeCardNumberForm(formDiv) {
        const idInput = formDiv.querySelector('input[type="hidden"][name$="-id"]');
        const deleteCheckbox = formDiv.querySelector('input[type="checkbox"][name$="-DELETE"]');
        
        // Se o formulário tem ID, é um existente - marca para deletar
        if (idInput && idInput.value) {
            if (deleteCheckbox) {
                deleteCheckbox.checked = true;
            }
            formDiv.classList.add('removing');
        } else {
            // Se é novo, remove imediatamente do DOM
            formDiv.remove();
            updateFormIndices();
        }
    }

    function addRemoveEventToForm(formDiv) {
        const removeButton = formDiv.querySelector('.btn-remove-card-number');
        if (removeButton) {
            removeButton.addEventListener('click', function(e) {
                e.preventDefault();
                removeCardNumberForm(formDiv);
            });
        }

        // Adiciona formatação ao input de número do cartão
        // Procura por inputs dentro de input-with-button
        const inputWithButton = formDiv.querySelector('.input-with-button');
        if (inputWithButton) {
            const numberInput = inputWithButton.querySelector('input[type="text"]');
            if (numberInput) {
                addFormatEventToInput(numberInput);
                // Formata o valor inicial se houver
                numberInput.value = formatCardNumber(numberInput.value);
            }
        }
    }

    addButton.addEventListener('click', function(e) {
        e.preventDefault();
        
        const currentCount = parseInt(totalFormsInput.value);
        
        // Cria a estrutura HTML correta para o novo form
        const newFormDiv = document.createElement('div');
        newFormDiv.className = 'card-number-form mb-20';
        newFormDiv.dataset.formIndex = currentCount;
        
        // Monta o HTML com a estrutura correta
        const inputHtml = emptyFormInput ? emptyFormInput.innerHTML.replace(/__prefix__/g, currentCount) : '';
        const idHtml = emptyFormId ? emptyFormId.innerHTML.replace(/__prefix__/g, currentCount) : '';
        const deleteHtml = emptyFormDelete ? emptyFormDelete.innerHTML.replace(/__prefix__/g, currentCount) : '';
        const nameHtml = emptyFormName ? emptyFormName.innerHTML.replace(/__prefix__/g, currentCount) : '';
        const homeHtml = emptyFormHome ? emptyFormHome.innerHTML.replace(/__prefix__/g, currentCount) : '';
        const dependenteHtml = emptyFormDependente ? emptyFormDependente.innerHTML.replace(/__prefix__/g, currentCount) : '';
        
        newFormDiv.innerHTML = `
            <div class="form-group-inline">
                <label>Nome</label>
                ${nameHtml}
            </div>
            <div class="form-group-inline">
                <label>Número do Cartão</label>
                <div class="input-with-button">
                    ${inputHtml}
                    <button type="button" class="btn-remove-card-number">Remover</button>
                </div>
            </div>
            <div class="form-group-inline">
                <label>Dependente</label>
                ${dependenteHtml}
            </div>
            <div class="form-group-inline home-screen-wrapper">
                ${homeHtml}
            </div>
            ${idHtml}
            ${deleteHtml}
        `;
        
        container.appendChild(newFormDiv);
        
        // Atualiza o contador de forms
        totalFormsInput.value = currentCount + 1;
        
        // Reconstrói os índices
        updateFormIndices();
        
        // Adiciona evento de remove para o novo campo
        addRemoveEventToForm(newFormDiv);
        
        // Move o cursor para o novo input
        const numberInput = newFormDiv.querySelector('.input-with-button input[type="text"]');
        if (numberInput) {
            numberInput.focus();
        }
        // Garante que o checkbox home_screen tenha um label clicável
        const homeCheckbox = newFormDiv.querySelector('input[type="checkbox"][name$="-home_screen"]');
        if (homeCheckbox) {
            let label = newFormDiv.querySelector('label.home-screen-label');
            const wrapper = newFormDiv.querySelector('.home-screen-wrapper');
                if (!label) {
                label = document.createElement('label');
                label.className = 'home-screen-label';
                label.setAttribute('for', homeCheckbox.id);
                const stateText = homeCheckbox.checked ? 'Ativado' : 'Desativado';
                label.textContent = `Tela Inicial: ${stateText}`;
                if (wrapper) wrapper.appendChild(label);
            } else {
                label.setAttribute('for', homeCheckbox.id);
                const stateText = homeCheckbox.checked ? 'Ativado' : 'Desativado';
                label.textContent = `Tela Inicial: ${stateText}`;
            }
            label.addEventListener('click', function(e) {
                e.preventDefault();
                homeCheckbox.checked = !homeCheckbox.checked;
                const stateText = homeCheckbox.checked ? 'Ativado' : 'Desativado';
                label.textContent = `Tela Inicial: ${stateText}`;
            });
        }
    });

    // Adiciona listeners aos forms existentes
    document.querySelectorAll('.card-number-form').forEach(addRemoveEventToForm);

    // Before submitting the parent form, synchronize TOTAL_FORMS with DOM
    (function attachSubmitSync() {
        const parentForm = container.closest('form');
        if (!parentForm) return;
        parentForm.addEventListener('submit', function() {
            const currentForms = container.querySelectorAll('.card-number-form').length;
            if (totalFormsInput) totalFormsInput.value = currentForms;
        });
    })();

    // Garante labels clicáveis para checkboxes já existentes na página
    document.querySelectorAll('.card-number-form').forEach(formDiv => {
        const homeCheckbox = formDiv.querySelector('input[type="checkbox"][name$="-home_screen"]');
        if (homeCheckbox) {
            let label = formDiv.querySelector('label.home-screen-label');
            const wrapper = formDiv.querySelector('.home-screen-wrapper') || formDiv;
            if (!label) {
                label = document.createElement('label');
                label.className = 'home-screen-label';
                label.setAttribute('for', homeCheckbox.id);
                const stateText = homeCheckbox.checked ? 'Ativado' : 'Desativado';
                label.textContent = `Tela Inicial: ${stateText}`;
                wrapper.appendChild(label);
            } else {
                label.setAttribute('for', homeCheckbox.id);
                const stateText = homeCheckbox.checked ? 'Ativado' : 'Desativado';
                label.textContent = `Tela Inicial: ${stateText}`;
            }
            label.addEventListener('click', function(e) {
                e.preventDefault();
                homeCheckbox.checked = !homeCheckbox.checked;
                const stateText = homeCheckbox.checked ? 'Ativado' : 'Desativado';
                label.textContent = `Tela Inicial: ${stateText}`;
            });
        }
    });
})();
