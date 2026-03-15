if st.session_state.editar[key]:

    # Cursos disponibles con placeholder
    cursos_disponibles = sorted(df_alumnos["Curso"].unique())
    cursos_opciones = ["Curso"] + cursos_disponibles
    curso = st.selectbox(
        "",
        cursos_opciones,
        key=f"curso_{key}"
    )
    if curso == "Curso":
        curso = None

    # Alumnos disponibles según curso seleccionado
    if curso:
        nombres_f = df_alumnos[df_alumnos["Curso"]==curso]["Nombre"]
        alumnos_opciones = ["Alumno"] + sorted(nombres_f)
        alumno = st.selectbox(
            "",
            alumnos_opciones,
            key=f"alumno_{key}"
        )
        if alumno == "Alumno":
            alumno = None
    else:
        alumno = None

    # Profesores con placeholder
    profesores_opciones = ["Profesor"] + lista_profesores
    profesor = st.selectbox(
        "",
        profesores_opciones,
        key=f"prof_{key}"
    )
    if profesor == "Profesor":
        profesor = None

    if st.button("Registrar entrada",key=f"entrada_{key}") and curso and alumno and profesor:

        st.session_state.ocupacion[
            st.session_state.planta][bano].append({

            "alumno":alumno,
            "curso":curso,
            "profesor":profesor,
            "h_entrada":datetime.now().strftime("%H:%M")

        })

        st.session_state.editar[key]=False
        st.rerun()
