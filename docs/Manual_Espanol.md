# VisionEdge 2.4.0 · Manual de uso

Español · Operadores e ingenieros de configuración · 2026-09-25

> Versión apta para una prueba piloto supervisada. Aún no se ha validado en la línea real la precisión, el hardware ni la operación prolongada. No utilice esta versión como único criterio para liberar producto. Este manual describe las funciones implementadas; no incluye corrección de rotación ni APL.

## 1. Primer uso: plantillas, reglas y después flujo

VisionEdge 2.4.0 conserva la captura y el marcado como tarea principal, siguiendo la facilidad de uso de tm_app. La inspección visual normal no necesita SOP. Active la secuencia de Flow Studio solo cuando el trabajo deba realizarse en orden.

| Entrada | Trabajo | Paso siguiente |
| --- | --- | --- |
| Inspección en vivo → Configuración | Controlador, resolución, fuente, producto y frecuencia | Confirmar una imagen correcta que se actualiza |
| Captura y etiquetas → Producto | Crear o seleccionar número de parte | Comprobar qué producto se está editando |
| Captura de cámara | Vista en vivo y controles Qualcomm compatibles | Fijar cámara e iluminación antes de capturar |
| Capturar imagen de plantilla | Capturar, ampliar, marcar y guardar una etiqueta independiente | Pulsar Guardar etiqueta en cada borrador |
| Biblioteca de etiquetas | Nombre, umbral, tolerancia y referencias por etiqueta | Guardar la fila, probar y aplicar |
| Aplicar inspección | Crear inspección básica ALL si todavía no hay reglas | Validar piezas correctas y defectuosas en vivo |
| Reglas / Flow Studio | Formar grupos con etiquetas guardadas; secuencia opcional | Guardar, aplicar y verificar el flujo completo |

Fijar una imagen solo conserva una captura de trabajo en esta sesión. Guardar etiqueta escribe la biblioteca. Aplicar inspección o Guardar y aplicar entrega la configuración al motor de producción. Un cambio guardado pero no aplicado todavía no es la configuración activa.

El ingeniero nuevo debe completar los capítulos 2, 3 y 5 antes de configurar el embalaje de los capítulos 4 y 6. El operador solo selecciona el producto, coloca las piezas y atiende las indicaciones.

## 2. Desde cero: configuración del equipo

### Secuencia de puesta en marcha

1. Solicite al responsable la dirección del equipo con el servicio iniciado y confirme la versión instalada. Este manual no presupone que una computadora nueva tenga controladores y dependencias Python instalados.
2. Abra Configuración y seleccione la opción de vista de cámara sin producto. Verifique la imagen antes de crear una inspección.
3. Configure controlador, fuente, resolución y orientación según la tabla. Pulse Aplicar configuración; si estaba detenida, vuelva a la vista en vivo e inicie la cámara.
4. Compruebe que la imagen no esté negra ni congelada y que la orientación sea correcta. Mueva un objeto para verificar la actualización.
5. Fije cámara, luz y dispositivo. Después cree las plantillas. Cambiar resolución, orientación, corrección de lente o posición de cámara exige volver a validar las regiones.

| Campo | Cómo elegir | Precaución práctica |
| --- | --- | --- |
| Cámara | En el equipo suele ser la cámara 0 | La fuente USB de una PC se selecciona en los ajustes avanzados |
| Resolución | Opciones 1920×1080 y 3840×2160; confirme soporte del equipo | Más píxeles aumentan la carga y no garantizan más precisión |
| Orientación | 0° o 180° para dejar la imagen derecha | No corrige automáticamente una caja girada |
| Corrección de distorsión de lente | Conserve el ajuste validado para el equipo | No es una calibración universal para cualquier cámara OpenCV |
| Producto de inspección | Seleccione el producto después de crearlo | Sin producto solo hay vista previa, no una decisión válida del producto |
| Velocidad de inspección | Comience con 5 por segundo; también hay 2 y 10 | Es la frecuencia objetivo; confirme la real en la vista en vivo |
| Calidad de grabación | Automática como punto inicial; opciones 8/16/24 Mbps | Afecta tamaño y calidad del video, no el umbral de reconocimiento |
| Espacio reservado | 5/10/20 GB; inicial 10 GB | No es una cuota máxima del historial ni un sistema de limpieza automática |
| Controlador, ajustes avanzados | Auto para el equipo validado; OpenCV fallback para pruebas en PC | Qualcomm QTI requiere hardware y controlador compatibles |
| Fuente de prueba | En OpenCV use 0 para la primera cámara disponible, o una ruta de video accesible por el servidor | La ruta pertenece a la computadora que ejecuta VisionEdge, no necesariamente a la del navegador |
| Descartar cambios | Recuperar los ajustes guardados del equipo | No deshace plantillas que ya fueron guardadas |

Ejemplo en PC: seleccione OpenCV fallback y fuente `0`; aplique e inicie la cámara. Para reproducir una prueba, use una ruta real como `D:/test/packing_trial.mp4`. El archivo debe existir en el servidor. En empaque, el video debe incluir un área vacía al inicio; de lo contrario el ciclo esperará el vaciado. Esta prueba no sustituye la aceptación con cámara real.

Cargar un video dentro de la configuración de flujo sirve para extraer plantillas. Seleccionar un video como fuente del equipo sirve para inspeccionarlo continuamente. Son funciones distintas.


### Ajustes de captura Qualcomm (2.4.0)

1. En Captura y etiquetas pulse Iniciar / Vista en vivo y espere una imagen estable. Consultar estado de cámara vuelve a leer las capacidades disponibles.
2. Abra Ajustes de cámara Qualcomm. Si indica que la cámara no es QTI o que la compatibilidad no está confirmada, los controles desactivados no se están aplicando; revise equipo y controlador.
3. Empiece con modo compatible: solo escribe balance de blancos. Conservar ajustes del dispositivo no escribe estos controles; modo manual permite los parámetros admitidos por el firmware.
4. Para aclarar u oscurecer pruebe pequeños cambios de compensación de exposición. Use el rango mostrado. Si el firmware ofrece nombres de modos, se presentan en un selector; no interprete códigos numéricos como microsegundos o distancia focal.
5. Pulse Guardar y reiniciar cámara. Se avisa antes de descartar regiones sin guardar. Finalice o aborte la pieza/caja y detenga la grabación antes de cambiar estos ajustes.
6. Espere la recuperación y compruebe estado e imagen. Una lectura correcta confirma el valor aceptado por el controlador, pero debe verificar brillo y color visualmente. Vuelva a capturar y validar las plantillas después del cambio.

| Control | Rango permitido por software | Uso |
| --- | --- | --- |
| Balance de blancos | 0–10; el valor debe estar admitido | Único control en modo compatible; use nombres del firmware si aparecen |
| Compensación de exposición | -12–12 | Ajuste poco a poco; observe sombras, reflejos y saturación. No son microsegundos |
| Modo ISO | 0–8 | Depende del dispositivo; confirme un modo compatible antes de usar ISO manual |
| ISO manual | 100–3200 | Depende del equipo y modo ISO; observe ruido y brillo |
| Antiparpadeo | 0–3 | Seleccione según opciones del firmware y luz del puesto; compruebe las bandas |
| Contraste | 1–10 | Evite perder detalle en luces y sombras |
| Saturación | 0–10 | Ajusta color; la comparación actual usa principalmente escala de grises y no garantiza distinguir solo por color |
| Nitidez | 0–6 | Realce de imagen, no enfoque óptico; no recupera desenfoque fuerte |

El rango efectivo se limita además por el controlador. Se informa si un control no existe, falla al escribir o devuelve un valor distinto. Si el modo manual impide arrancar, vuelva al modo compatible o a conservar los ajustes del dispositivo, reinicie y consulte el estado.

No hay un deslizador universal de distancia focal/enfoque óptico. Requiere una interfaz específica del módulo y firmware aún no validada en hardware. El zoom 100%/200% del editor no enfoca el objetivo. Captura y producción comparten los ajustes de cámara; no hay exposición independiente por etiqueta.

## 3. Capturar, ampliar, marcar y configurar cada etiqueta

### Primera etiqueta desde la cámara

1. Abra Captura y etiquetas. Cree `DEMO-LABEL` en el panel de producto y compruebe que esté seleccionado.
2. Coloque una pieza correcta en su posición. Use Iniciar / Vista en vivo para revisar imagen, enfoque e iluminación. Pulse Capturar desde cámara para congelar la imagen de trabajo.
3. Escriba `LABEL_OK_01` en Nombre de etiqueta nueva, seleccione candidato OK y pruebe inicialmente un umbral de `0.80`. El umbral inicial solo afecta las regiones nuevas; no modifica etiquetas guardadas.
4. Si la imagen es pequeña, pulse 100% o 200%. 100% representa los píxeles originales; 200% amplía la pantalla sin crear detalle. También puede usar +/− o Ctrl + rueda.
5. Busque el objetivo con las barras de desplazamiento o active Desplazar imagen y arrastre con el botón izquierdo. Desactive ese modo antes de marcar. El botón central permite desplazar sin cambiar el modo de marcado.
6. Arrastre con el botón izquierdo desde la esquina superior izquierda hasta la inferior derecha del objetivo. Seleccione texto, figuras o bordes distintivos; evite fondos uniformes, manos y reflejos temporales.
7. En la fila de borrador ajuste nombre, umbral y tolerancia, por ejemplo `LABEL_OK_01`, `0.85` y `8`. Pulse Guardar etiqueta. Si el recorte está mal, elimine ese borrador y marque de nuevo.
8. El borrador desaparece y aparece una fila en la biblioteca cuando se guarda correctamente. No se crea ningún paso SOP ni se requiere asignar a un Step.
9. Repita para otras apariencias correctas o errores conocidos. Una plantilla NG debe distinguir el defecto; no coincidir con una plantilla OK no significa coincidir con una NG.

### Campos por etiqueta

| Campo | Uso |
| --- | --- |
| Nombre de etiqueta | Editable en su fila. Use propósito y posición, como A_IZQUIERDA o SEAL_OK. No necesita un nombre fijo del sistema. |
| Umbral de coincidencia | Independiente por fila, de 0 a 1. Coincide si la puntuación es mayor o igual. 0 es válido, pero prácticamente elimina el filtro; no es un punto de partida apropiado para producción. |
| Tolerancia de posición | Píxeles de la imagen original. 0 busca en toda la imagen; un valor positivo limita la búsqueda cerca del recorte original. Por ejemplo 8 permite buscar aproximadamente 8 píxeles alrededor. No representa ángulo ni comprueba que el objeto completo esté dentro del recuadro. |
| Tipo sugerido | OK, NG o Neutral orienta la selección. El rol real de reglas existentes se cambia dentro de la regla; modificar esta sugerencia no invierte un rol OK existente. |
| Reglas que la utilizan | Producto y nombre de regla. Cambiar nombre, umbral o margen actualiza sus copias en las reglas; vuelva a aplicar los otros productos afectados. |
| Guardar etiqueta | Guarda esa fila. Los cambios pendientes de otras filas se conservan y deben guardarse por separado. |
| Eliminar | Se rechaza si hay referencias en reglas o condiciones de embalaje. Quite esas referencias y compruebe otros productos antes de eliminar. |

Las coordenadas x/y/w/h guardadas corresponden a la imagen original, independientemente del zoom. El embalaje utiliza su tolerancia común; pruebe por separado las etiquetas y el ciclo de embalaje.

### Editar una etiqueta guardada

1. Cambie nombre, umbral o tolerancia en la fila y pulse Guardar etiqueta. El sistema avisa si se actualizarán reglas que la utilizan.
2. Si otra página o persona modificó la etiqueta, se rechaza la escritura con una versión antigua. Anote los cambios pendientes, recargue, compare y edite de nuevo.
3. Finalice o aborte la pieza/caja y detenga la grabación antes de cambiar etiquetas usadas por el producto activo.
4. Para cambiar foto o ROI, capture y guarde una etiqueta nueva. Selecciónela en las reglas, quite la referencia anterior, guarde, aplique y vuelva a probar. La biblioteca no permite arrastrar las esquinas de un recorte ya guardado.

Se avisa de cambios sin guardar al cambiar producto, salir o recargar. Guarde los borradores importantes antes de cambiar la imagen de trabajo. Fijar una captura no es una copia de seguridad persistente.

### Probar y aplicar

Guarde todos los borradores y filas antes de Probar etiquetas guardadas. La tabla muestra puntuación, umbral y coincidencia usando la imagen actual de la cámara, no la captura antigua fijada. No avanza el SOP ni crea historial de producción. Una marca ✓ en una etiqueta NG significa que se encontró el defecto conocido; no significa producto aprobado.

Si no hay reglas, Aplicar inspección propone crear un grupo básico ALL: todas las etiquetas OK deben coincidir y cualquier NG rechaza; Neutral no se agrega y SOP permanece desactivado. Se requiere al menos una etiqueta OK. Con reglas existentes, solo se aplican esas reglas: una etiqueta nueva no se incorpora automáticamente. Revise sus referencias en Flow Studio.

Para tomar muestras de un video: seleccione archivo → reproduzca o mueva la línea de tiempo → pause/capture → escriba nombre y tipo → amplíe y marque → guarde la etiqueta. No marque durante reproducción. Para inferencia continua de un video, configúrelo como fuente del equipo; cargarlo en el editor solo sirve para obtener muestras.

## 4. Reglas y campos avanzados del flujo

| Nivel | Ejemplo | Selección correcta |
| --- | --- | --- |
| Alternativas en un grupo | Dos versiones válidas de una etiqueta | Dos muestras OK en el mismo grupo, ANY |
| Requisitos simultáneos en un grupo | Tornillo izquierdo y derecho | Muestras de ambos, ALL; asegúrese de que no puedan coincidir con el mismo tornillo |
| Resultado entre grupos | Etiqueta y sello obligatorios | Resultado de imagen con ALL entre grupos |
| Secuencia temporal | Primero A, después B | Dos pasos y SOP habilitado; no ANY entre grupos |

Varias plantillas de objetos iguales no garantizan conteo. Sin restricciones de posición pueden coincidir con el mismo objeto. En la pantalla general las nuevas plantillas tienen search_margin 0 y no hay un campo individual de margen; no debe prometerse una comprobación estricta de ubicación con esa configuración. El modo de empaque aplica su tolerancia de posición a las plantillas de ciclo y pasos.

| Ajuste del panel izquierdo | Función | Configuración inicial para trabajo secuencial |
| --- | --- | --- |
| Nombre de estación | Identificación, por ejemplo PACK-01 | No crea otro producto |
| Inspección en orden | Activa SOP | Desactivado en el ejemplo por foto; activado automáticamente en empaque |
| Orden estricto / alarma por salto | Detecta un paso posterior realizado antes del esperado | Activar; empaque lo impone |
| Alarma por tiempo excedido | Permite las alarmas configuradas por paso | Requiere además un tiempo por paso distinto de cero |
| Mantener alarma hasta reconocimiento | No desaparece solo porque mejora la imagen | Activar; empaque lo impone |
| Sonido web | Aviso del navegador | El navegador debe haber recibido una interacción del usuario |
| Reinicio al completar | Manual o por retardo | Empiece con manual; el retardo puede reiniciar sobre la misma pieza que aún no se retiró |
| Segundos de retardo | Solo para reinicio por tiempo | No se utiliza en empaque |
| Torre de luces y canales DO | Campos reservados | Esta versión no implementa una salida física utilizable |

Abra las condiciones avanzadas de cada paso. Un paso nuevo normalmente está habilitado y es obligatorio, con 2 coincidencias consecutivas, 400 ms de permanencia y tiempo máximo 0.

| Campo del paso | Significado / rango | Ejemplo o error frecuente |
| --- | --- | --- |
| Habilitado | Participa en el flujo | No deshabilite un requisito para eliminar una alarma |
| Obligatorio | SOP debe completarlo | A y B obligatorios; no significa que un grupo opcional quede automáticamente excluido de la decisión por foto |
| ANY/ALL del grupo | Relación entre muestras OK | ANY para variantes; ALL para requisitos simultáneos |
| Coincidencias consecutivas | 1–120 evaluaciones seguidas | No equivale a contar imágenes capturadas por la cámara |
| Permanencia en ms | 0–600000; se cumple junto con el número de coincidencias | 400 ms = 0.4 s; menor frecuencia real puede aumentar la espera |
| Tiempo máximo en segundos | 0–86400; 0 desactiva el límite del paso | Mida el trabajo antes de fijarlo; 10 s puede servir para practicar, no es un estándar |
| Permitir anticipación | Admite pasos adelantados en flujos generales | Se desactiva en empaque |
| Mantener completado | Conservar DONE o permitir volver a pendiente | Para A que luego se cubre suele mantenerse; la visibilidad final se configura aparte |
| Alarma por paso omitido | Alarma si se omite este paso esperado | Mantener para requisitos; funciona junto con orden estricto |
| Artículo visible al final | Volver a comprobarlo al terminar el empaque | Marque A y B si ambos son visibles; no desmarque solo para conseguir aprobación |

Use flechas arriba/abajo o el asa para ordenar. Duplicar ayuda a crear pasos similares, pero debe cambiar nombre y plantillas para no comprobar dos veces el mismo lugar. Un paso vacío necesita una muestra OK antes de aplicar.

## 5. Caso práctico: etiqueta y sello sin SOP

Objetivo: deben estar presentes la etiqueta correcta y el sello; una etiqueta errónea conocida debe rechazar inmediatamente.

1. Cree `PACK-LABEL`, coloque etiqueta y sello correctos y capture.
2. Marque por separado y guarde `LABEL_OK` y `SEAL_OK`, ambas de tipo OK, con umbrales independientes. Evite unir objetos y mucho fondo en un único recorte.
3. Para comprobar posición use tolerancias positivas, por ejemplo 8 píxeles por etiqueta. Si la posición no es estable, mejore primero el útil.
4. Coloque una etiqueta errónea conocida y guarde `LABEL_WRONG` de tipo NG. No seleccione solo el fondo blanco común a todas las etiquetas.
5. Pruebe pieza correcta, sin etiqueta, sin sello, etiqueta equivocada y posición incorrecta. Registre las puntuaciones y compruebe que NG no coincida con piezas correctas.
6. Pulse Aplicar inspección y confirme la creación de ALL con rechazo prioritario NG. No active la inspección secuencial.
7. En Inspección en vivo use Inspección por foto con los mismos casos y compruebe resultado e historial. Finalice la pieza antes de cambiar a otra.

Si hay dos etiquetas válidas A/B, no exija ambas mediante ALL. Guarde la segunda apariencia y abra Reglas / Flow Studio. Cree un grupo de etiqueta con A/B y seleccione cualquier OK (ANY); cree otro grupo para el sello. Exija todos los grupos (ALL) en la imagen. Cada grupo necesita una plantilla OK; asigne NG al grupo correspondiente.

Ejemplo de ajuste: si la menor puntuación correcta es 0.92 y la mayor defectuosa 0.71, puede probar 0.85 y validar después con muestras independientes. Son números hipotéticos, no una garantía. Si se superponen las puntuaciones, cambie recorte, luz o posicionamiento. Guarde la fila y aplique después de cada ajuste.

## 6. Caso práctico: A en posición 1, B en posición 2 y cambio automático

Objetivo: mesa vacía → caja vacía colocada → A a la izquierda → B a la derecha → conjunto completo → retirada y cierre. Fije cámara, orientación de caja y alojamientos. Esta versión no corrige automáticamente la rotación.

### Primero guarde cinco etiquetas independientes

1. Cree `BOX-AB`. Con la zona vacía capture toda el área de caja y guarde `AREA_CLEAR` de tipo Neutral.
2. Coloque una caja vacía. Capture su interior y guarde `BOX_EMPTY`, Neutral. Debe dejar de coincidir al introducir objetos.
3. Capture una parte del borde o característica que siga visible durante el llenado como `BOX_PRESENT`, Neutral. No debe coincidir sin caja o con mala colocación.
4. Coloque A a la izquierda y guarde `A_LEFT`, OK, con características distintivas y posición correcta.
5. Coloque B a la derecha y guarde `B_RIGHT`, OK. Pruebe primero las puntuaciones y tolerancias individuales.

### Después configure el flujo

1. Abra Reglas / Flow Studio y agregue dos grupos: A a la izquierda y B a la derecha. En cada grupo seleccione las plantillas OK/NG y asigne A_LEFT o B_RIGHT como OK. Pulse Listo.
2. Active la inspección en orden. A debe quedar antes de B; use flechas o arrastre para ordenar. Puede empezar la práctica con 2 coincidencias consecutivas y 400 ms; valide los valores con el ritmo real.
3. Active inicio y cambio de caja por imagen. Seleccione el modo de caja/bandeja que se retira. Asigne AREA_CLEAR a zona vacía, BOX_EMPTY a caja vacía y BOX_PRESENT a referencia de posición. Estas tres plantillas son condiciones de ciclo, no pasos de piezas.
4. Como inicio pruebe margen común de 8 píxeles, estabilidad de 0.8 s y confirmación final de 1 s. El margen de embalaje se usa tanto en condiciones de ciclo como en muestras del flujo; no usa los márgenes individuales de la prueba de etiquetas.
5. Si A y B quedan visibles al final, mantenga activada la verificación final de ambos pasos. Guarde y aplique; vuelva a la pantalla en vivo.

### Validación de un ciclo

| Acción | Resultado esperado |
| --- | --- |
| Arrancar con caja presente | Solicitar vaciar primero; no recuperar un progreso desconocido |
| Vaciar la zona | Tras estabilidad, esperar caja vacía |
| Colocar caja vacía con referencia visible | Iniciar una caja y pedir A |
| Colocar A a la izquierda | Completar A; en la derecha no debe completarse |
| Colocar B a la derecha, manteniendo A | Completar B y pedir retirar tras confirmación estable |
| Retirar y mostrar la mesa vacía | Registrar un solo resultado aprobado y esperar otra caja |
| Dejar la misma caja en la imagen | No incrementar repetidamente el contador |

Pruebe también B antes de A, retirada anticipada, piezas ausentes, mala posición, coincidencia NG, mano sobre referencia, quitar A al final y pérdida de cámara. Una obstrucción no equivale a retirada. Tras interrupción, vacíe y comience de nuevo.

Para útil fijo seleccione retirar solo objetos: la zona vacía es el interior del útil y la referencia una característica fija. No usa etiqueta de caja vacía. Mantenga la secuencia A/B y retire todas las piezas para cambiar de ciclo.

Si el embalaje tapa A al final, puede desactivar solo su verificación final y conservar B. Esto demuestra que A estuvo presente, no que sigue dentro después de quedar oculta. Si necesita esa garantía, cambie el ángulo de cámara o el procedimiento.

## 7. Elegir el modo de trabajo

| Modo | Uso | Inicio | Registro |
| --- | --- | --- | --- |
| Inspección por foto | Verificar las condiciones de una imagen | Botón de inspección por foto o Enter en el campo de serie | Guarda imagen original, resultado y detalles de cada intento |
| Inspección continua / SOP | Probar reconocimiento o seguir pasos | Iniciar cámara y aplicar el producto | Actualiza resultados; no guarda una inspección por cada imagen |
| Empaque automático | Colocar artículos en orden y cambiar de caja | Vaciar el área y colocar una caja vacía | Guarda eventos de inicio, pasos, alarmas, verificación final y retiro |

Guardar una imagen no equivale a realizar una inspección por foto. Aprobar una foto no confirma que se haya completado todo el SOP. La inspección manual por foto se desactiva durante el empaque automático.

## 8. Al comenzar el turno

1. Compruebe que la cámara, la iluminación y la estación estén fijas. Oriente la caja como en las imágenes usadas para crear las plantillas.
2. Abra en el navegador la dirección del equipo proporcionada por el ingeniero. No se requiere inicio de sesión. Seleccione Español en el menú superior de idioma.
3. Confirme el producto o número de parte y pulse Iniciar cámara.
4. Verifique que la imagen se actualice, la inspección esté lista y haya espacio de almacenamiento. No debe haber cambios pendientes de aplicar.
5. Compruebe una pieza buena y una pieza con defecto conocido. En empaque, pruebe también un ciclo completo de vaciado, carga y retiro.

Si la imagen se congela, el equipo se desconecta o la inspección no está lista, deje de utilizar sus resultados y avise al ingeniero.

## 9. Operador: inspección por foto

1. Confirme que el empaque automático esté desactivado y coloque la pieza en su posición de referencia.
2. Introduzca o escanee el número de serie si necesita trazabilidad. Si la serie es obligatoria, no podrá inspeccionar sin ella.
3. Pulse «Inspección por foto» y espere a que termine la evaluación y el guardado. Enter en el campo de serie también activa la inspección.
4. Revise el resultado: «APROBADO», «No conforme» o «Requiere revisión · ajuste y vuelva a tomar la foto». Un resultado pendiente no es una aprobación.
5. Para corregir y repetir la inspección de la misma pieza, pulse «Volver a inspeccionar con foto». Cada intento conserva su propio registro y la serie permanece bloqueada.
6. Pulse Finalizar pieza antes de pasar a otra. Cerrar la pieza no convierte un rechazo en aprobación.

Corrija la causa antes de repetir. No reduzca el umbral únicamente para conseguir que una pieza defectuosa pase.

## 10. Operador: empaque automático

Secuencia normal: **área vacía → caja vacía en posición → artículo A → artículo B → verificación final → retirar caja → siguiente caja**.

| Indicación | Acción |
| --- | --- |
| Vaciar primero el área | Retire caja y artículos; deje visible toda el área de referencia |
| Esperando la siguiente caja | Coloque una caja vacía con la referencia visible; espere la indicación de colocar artículos |
| Colocar artículos en orden | Siga el paso indicado y espere la confirmación antes del siguiente |
| Esperando confirmación / referencia poco clara | Retire las manos u obstáculos y compruebe la posición de la caja |
| Verificación final completa; retirar | Retire toda la caja y deje vacía el área; entonces se registra la aprobación final |
| Problema de inspección | Corrija faltantes, muestras NG, orden incorrecto u otras causas antes de continuar |

Con un dispositivo de sujeción fijo no se coloca una caja vacía: después del vaciado, el ciclo comienza al reconocer un artículo junto con la referencia de posición. Los artículos deben colocarse en el orden establecido.

El retiro anticipado se registra como incompleto. Una misma caja que permanece en imagen no se cuenta varias veces. Detener la cámara, perder la imagen o cancelar requiere vaciar de nuevo; el progreso anterior no se reanuda automáticamente.

### Resolver un problema

- Si puede continuar con la misma caja, corrija primero la causa y seleccione la opción para confirmar que el problema se resolvió y continuar. Reconocer una alarma no aprueba la caja: las condiciones se vuelven a verificar.
- Si no puede confirmar el contenido, cancele la caja, sepárela para revisión manual y vacíe el área antes de reiniciar.
- Si falla el guardado o falta espacio, detenga el trabajo y avise al ingeniero. Un resultado no guardado no constituye un registro válido.

## 11. Ingeniero: reglas y entrega de cambios

1. Edite las plantillas en Captura y etiquetas y después abra Reglas / Flow Studio.
2. Cada grupo necesita al menos una plantilla OK. ANY acepta apariencias alternativas; ALL exige condiciones simultáneas. Cualquier NG de un grupo habilitado tiene prioridad de rechazo.
3. Mantenga desactivada la secuencia si no necesita orden. Para embalaje revise pasos obligatorios, coincidencias consecutivas, duración, tiempo límite y visibilidad final.
4. La × dentro de un grupo elimina la referencia, no la etiqueta de la biblioteca. Reutilizar una etiqueta implica que sus cambios afectan otros productos que la usan.
5. Listo solo cierra el selector. Después use Guardar y aplicar. Si se guardó pero falló la aplicación, resuelva el mensaje; no dé por activa la configuración nueva.
6. Documente producto y estación, resolución y controles de cámara, propósito y umbral de cada etiqueta, márgenes, ANY/ALL, tiempos SOP, visibilidad final, pruebas correctas/defectuosas y ubicación de la copia de seguridad.

Para sustituir foto o ROI cree una etiqueta nueva y actualice las referencias necesarias antes de eliminar la anterior. Compruebe si otros productos la utilizan.

## 12. Ingeniero: configurar empaque automático

Active el inicio y cambio automático por imagen y elija caja/bandeja o útil fijo. Primero guarde las etiquetas de zona vacía, caja vacía y referencia en Captura y etiquetas; después selecciónelas en los tres desplegables de Flow Studio. No las agregue a los grupos de piezas.

| Condición | Región que debe marcar | Prueba necesaria |
| --- | --- | --- |
| Área vacía | Toda el área de la caja o el interior del dispositivo | No debe coincidir cuando hay una caja o artículos |
| Caja vacía en posición | Interior vacío de la caja; no se usa en modo fijo | Debe dejar de coincidir después de agregar artículos |
| Referencia de posición | Borde o característica fija visible después de cargar | No debe indicar presencia válida con mesa vacía, obstrucción o posición incorrecta |

Use plantillas distintas para las condiciones. No seleccione solamente un pequeño fondo que permanezca igual durante toda la operación. Si las condiciones de vacío y presencia se contradicen, el ciclo puede quedarse esperando.

La casilla que exige que el artículo siga visible al final define la verificación de conjunto. Normalmente se marca para todos los artículos visibles al terminar. Puede desmarcar un artículo temprano que será cubierto por empaque posterior, pero debe mantener al menos un paso para la verificación final. Un paso desmarcado demuestra que se aprobó antes, no que el artículo siga dentro de la caja.

| Parámetro | Rango / valor inicial | Significado |
| --- | --- | --- |
| Estabilidad de condición | 0.3–10 s / 0.8 s | Inicio y vaciado deben mantenerse; exige al menos tres observaciones |
| Verificación final | 0.3–10 s / 1 s | Las condiciones finales deben mantenerse; exige al menos tres observaciones |
| Tolerancia de posición | 1–100 píxeles / 8 | Limita la búsqueda de la plantilla; no es tolerancia angular ni prueba de contención completa |
| Frecuencia de inspección | Mínimo 2 por segundo en empaque / inicial 5 | Es un objetivo configurado, no una garantía de rendimiento; observe la frecuencia real |

El modo de empaque impone el orden de pasos, mantiene las alarmas hasta reconocerlas y desactiva el reinicio por tiempo. No cambie la configuración de una caja en curso: termínela o cancélela y detenga la grabación antes de modificar ajustes.

## 13. Historial, imágenes y grabaciones

En Historial de inspección, la parte superior contiene los registros de empaque automático. Abra la evidencia de pasos para consultar imagen original, resultado y detalles. La sección inferior contiene las inspecciones manuales y permite buscar por serie o identificador de registro. El empaque usa un identificador de caja generado por el sistema; aún no integra el bloqueo por serie/escaneo del modo manual.

«Esperando el retiro» no es una aprobación final registrada. Confirme el resultado aprobado después del retiro. Un ciclo incompleto o interrumpido no es aprobado.

En Fotos y grabaciones puede consultar, descargar y administrar medios. Detenga la grabación y espere el guardado antes de utilizar el video terminado. No cambie cámara o flujo durante una grabación. Las evidencias de eventos se guardan aparte: borrar fotos no limpia la base de datos de empaque.

## 14. Ingeniero: pruebas y polling

- Para probar reconocimiento, inicie la cámara y ajuste la frecuencia de inspección; observe los resultados continuos.
- Consulte `GET /api/edge/status` periódicamente. La consulta no crea una inspección. La interfaz espera aproximadamente 800 ms después de cada respuesta. Revise `inference_ready`, `definition_pending` y `packaging`; no utilice solo la última palabra de aprobación.
- Para crear una inspección por foto, envíe `POST /api/edge/inspection` con JSON que incluya `action: "capture"`, `request_id` en formato UUID y `sn`. Consulte primero GET en la misma ruta para obtener el estado; en repeticiones de la misma pieza conserve su `cycle_id` y serie. Reutilice request_id al reintentar una petición por fallo de red; use otro UUID para una inspección realmente nueva.
- Para cerrar una pieza manual, envíe a la misma ruta `action: "close"` y el `cycle_id` actual. Cierre la anterior antes de abrir otra. El modo automático rechaza capture.
- No hay un interruptor en la interfaz para guardar automáticamente una inspección cada N segundos. Tampoco hay una entrada dedicada PLC/GPIO ni una interfaz de enclavamiento industrial validada.

## 15. Diagnóstico y mantenimiento

| Problema | Primera acción |
| --- | --- |
| Cámara no lista / sin imagen | Revisar conexión, fuente y si otro proceso está usando la cámara |
| Espera permanente de vacío o caja | Revisar plantillas, orientación, iluminación, posición y contradicciones entre condiciones |
| Artículo presente pero rechazado | Revisar posición, rotación, obstrucción y plantilla; observar puntuaciones antes de cambiar umbrales |
| Pasos terminados, sin permiso de retiro | Revisar artículos finales visibles, NG y alarmas pendientes |
| Reinicio después de perder imagen | Separar la pieza anterior y reiniciar desde el área vacía; no se conserva el progreso |
| Sin espacio / error al guardar | Suspender el uso; respaldar y revisar capacidad y permisos con el ingeniero |

Detenga grabación y servicio antes de respaldar `db/`, `uploads/`, `runtime_data/`, `config/edge.ini` y certificados del equipo. El historial manual está en `runtime_data/inspection_history.sqlite3`; el de empaque, en `runtime_data/edge/packaging_history.sqlite3`. No copie solamente un archivo SQLite mientras el servicio escribe.

Ambos historiales crecen con el uso. No hay una administración completa de retención o rotación automática de estos registros. Asigne responsables de capacidad, respaldos y pruebas de restauración; la limpieza de medios no implica limpieza del historial.

En actualizaciones conserve datos, ajustes y certificados reales; no los sustituya con ejemplos. El punto de entrada para el ingeniero es `python visionedge_server.py`, con dependencias y configuración válidas. El operador debe seguir el procedimiento de inicio establecido en la estación.

## 16. Aceptación antes de producción

Evaluación actual: puede programarse un piloto supervisado; la liberación formal de producción requiere validación local.

- Probar cada producto con imágenes independientes y piezas reales: buenas, faltantes, equivocadas, fuera de posición, NG, pasos fuera de orden, retiro temprano, reflejos y obstrucciones. Definir previamente tasas aceptables de rechazo falso y aceptación incorrecta, y registrar resultados.
- Verificar cambio completo de caja, ausencia de conteo duplicado, vaciado obligatorio después de reiniciar, pérdida de cámara y almacenamiento insuficiente sin aprobación indebida.
- Operar un turno completo con resolución, cámara/QTI, grabación y ritmo reales; ampliar la duración según el proceso.
- Probar recuperación de energía, hora correcta, restauración de respaldos, lectura de evidencia y responsabilidades de mantenimiento.
- Al no requerir inicio de sesión, quien tenga acceso al equipo puede modificar ajustes o datos. Use una red de producción controlada y gestione el acceso en la planta.

Validación de esta versión: 13 scripts aprobados, incluidas referencias de etiquetas, controles QTI simulados, 13 pruebas del ciclo y comparación de imágenes sintéticas. Se omitió un script heredado de WebSocket porque falta websocket-client. Se probó en navegador capturar, ampliar, guardar/editar, probar y aplicar etiquetas. Quedan pendientes la cámara Qualcomm real, el enfoque óptico y el ritmo de producción.

Límites conocidos: no hay corrección automática de rotación ni reconocimiento general de objetos o manos. No puede demostrarse que el contenido no cambió durante una obstrucción. Si la caja se oculta después de la verificación final y luego se retira, el sistema puede cerrar el ciclo usando la verificación anterior. Si el proceso debe impedir esta situación, se necesita control adicional de visibilidad o revisión humana. Una imagen pausada por referencia poco clara no significa aprobación.

