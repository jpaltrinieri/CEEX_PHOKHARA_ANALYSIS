! T4: evaluate the CEEX-main pipig 1-photon NLO pieces at phase-space points dumped
! by PHOKHARA (RUN_PHOKHARA variant phokhara_dump, file t4_points.txt).
!
!   cd $CEEX_ROOT       (GoSam process libraries are on a relative rpath)
!   T4_IN=<t4_points.txt> T4_OUT=<out.txt> <this binary> \
!       --process=pipig --scenario=KLOE-LA --NLO --emin=1d-5 --outdir=<dir>/
!
! Input rows: iswap qq  e+(4) e-(4) gamma(4) pi+(4) pi-(4)  ... (E,px,py,pz; e+ along +z).
! CEEX order: m(1)=e+, m(2)=e-, m(3)=pi+, m(4)=pi-, m(5)=gamma, m(i,1:4)=(E,px,py,pz).
! Output rows: iswap  tree  aD  act  YFSv  YFS  amp2  amp2chk
!   tree = |M_tree|^2 (GoSam, x e^6), aD = alpha/4pi * D (hard virtual incl. mass CT),
!   act = 2 alpha/4pi * ct_pipi, YFSv = Re B4totVirtual, YFS = B4tot (real+virtual soft,
!   E_gamma < Emin), amp2 = amp2_pipig_NLO(1), amp2chk = tree*(1 + aD + act - YFSv + YFS).
! The pion mass is set to PHOKHARA's 0.13957039 GeV so its momenta are on shell.
program t4_ceex
   use M_PARAMETERS
   use M_USER_PARAMETERS
   use M_INIT
   use M_GOSAM_INIT
   use M_COLLIER_INITIALISE
   use GL_QUAD
   use FORMFACTOR
   use M_COUNTERTERMS_PI
   use GOSAM_AMP_PIPIG_1L
   use M_FO_PIPIG
   implicit none
   integer :: seedval = 1, iu, ou, ios, iswap, n
   character(len=256) :: outdir
   character(len=512) :: fin, fout
   real(prec) :: row(22), tree, D, born, pole, ctf, YFSv, YFS, amp2, chk
   real(prec), allocatable :: ms(:,:)
   character(len=4096) :: line

   call get_environment_variable("T4_IN", fin)
   call get_environment_variable("T4_OUT", fout)
   if (len_trim(fin) == 0 .or. len_trim(fout) == 0) stop "set T4_IN and T4_OUT"

   call prepare_arguments(seedval, outdir)
   call check_arguments()
   call init_order()
   call init_sqrts()
   call init_formfactor()
   mpion = 0.13957039e0_prec
   call init_collier()
   call init_gosam()
   call init_gl()
   call prepare(1)
   allocate(ms(size(m,1),4))

   open(newunit=iu, file=trim(fin), status="old", action="read")
   open(newunit=ou, file=trim(fout), status="replace", action="write")
   write(ou,'(a)') "# iswap tree aD act YFSv YFS amp2 amp2chk   (CEEX-main, mpion=0.13957039)"
   n = 0
   do
      read(iu,'(a)', iostat=ios) line
      if (ios /= 0) exit
      if (line(1:1) == "#" .or. len_trim(line) == 0) cycle
      read(line, *) row
      iswap = nint(row(1))
      m(1,:) = row(3:6)      ! e+
      m(2,:) = row(7:10)     ! e-
      m(5,:) = row(11:14)    ! gamma
      m(3,:) = row(15:18)    ! pi+
      m(4,:) = row(19:22)    ! pi-
      tree = pipig_tree(m)*E3*E3
      D    = D_at(m, born, pole, ms)
      ctf  = real(ct_pipi(), prec)
      YFSv = real(B4totVirtual(m(1,:),m(2,:),m(3,:),m(4,:)), prec)
      YFS  = B4tot(m(1,:),m(2,:),m(3,:),m(4,:))
      amp2 = amp2_pipig_NLO(1)
      chk  = tree*(1e0_prec + ALPHA_QED/(4e0_prec*PI)*D + 2e0_prec*ALPHA_QED/(4e0_prec*PI)*ctf - YFSv + YFS)
      write(ou,'(i2,7(1x,es24.15))') iswap, tree, ALPHA_QED/(4e0_prec*PI)*D, &
            2e0_prec*ALPHA_QED/(4e0_prec*PI)*ctf, YFSv, YFS, amp2, chk
      n = n + 1
   end do
   close(iu); close(ou)
   write(*,'(a,i0,a)') "[t4_ceex] ", n, " points -> "//trim(fout)
end program t4_ceex
