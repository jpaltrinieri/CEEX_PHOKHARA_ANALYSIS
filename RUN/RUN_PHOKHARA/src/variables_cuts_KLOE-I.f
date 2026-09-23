c ========================================================================
c Histograms for dxs/variables for KLOE-I scenario in Strong2020. 
c ------------------------------------------------------------------------
      subroutine output_variables(n, value, i)
       ! n refers to a process with 0, 1 (n=0) or 2 (n=1) photons
       ! value is the weight for the MC histograms
       ! i is 0 (1) for the (un)weighted histograms
      include 'phokhara_10.0.inc'
      logical g1_pass_cuts, g2_pass_cuts
      integer n, i, k, g1_cuts, g2_cuts
      real*8 value, thp, thm, pp, pm, pzp, pzm, ppp, ppm
      real*8 mxx, xi, phip, phim, dphi, thav, thg, thg1
      real*8 thg2, eg, mxxg, mtrk, mxxc, mtrkc, s, a
      real*8 g1_energy, g2_energy
      real*8, allocatable :: variables(:)
      allocate(variables(1:total_num_hist))

      ! Calculate variables to plot
      s = momenta(3,0) + momenta(4,0) + momenta(6,0) + momenta(7,0)
      pp = dSqrt(momenta(6,1)**2+momenta(6,2)**2+momenta(6,3)**2)*1000
      pm = dSqrt(momenta(7,1)**2+momenta(7,2)**2+momenta(7,3)**2)*1000
      thp = dacos(-momenta(6,3)*1000/pp)
     &         *180.d0/pi
      thm = dacos(-momenta(7,3)*1000/pm)
     &         *180.d0/pi
      ppp = dSqrt(momenta(6,1)**2 + momenta(6,2)**2)*1000
      ppm = dSqrt(momenta(7,1)**2 + momenta(7,2)**2)*1000
      pzp = abs(momenta(6,3))*1000
      pzm = abs(momenta(7,3))*1000
      thav = (-thp+thm+180)/2
      xi = ABS(thp+thm-180)
      phip = atan2(momenta(6,2), momenta(6,1))*180.d0/pi
      phim = atan2(momenta(7,2), momenta(7,1))*180.d0/pi
      dphi = abs(abs(phip-phim) - 180)
      mxx =dSqrt((momenta(6,0) + momenta(7,0))**2 -
     &       (momenta(6,1) + momenta(7,1))**2 - 
     &       (momenta(6,2) + momenta(7,2))**2 - 
     &       (momenta(6,3) + momenta(7,3))**2) * 1000
      a = 1000000 * (s-dSqrt((momenta(6,1)+momenta(7,1))**2+
     &             (momenta(6,2)+momenta(7,2))**2+
     &             (momenta(6,3)+momenta(7,3))**2))**2
      mtrk = dSqrt(a/4 - (pp**2+pm**2)/2 + (pp**2-pm**2)**2/(4*a))
      mxxc = 0
      mtrkc = 1000 
      if (pion.eq.0.and.mtrk.lt.115.and.mtrk.gt.80) mxxc = mxx
      if (pion.eq.1.and.mtrk.lt.220.and.mtrk.gt.130) mxxc = mxx
      if (mxx**2.gt.500000.and.mxx**2.lt.700000) mtrkc = mtrk
      
      thg1 = dacos(-momenta(3,3)/
     &         dSqrt(momenta(3,1)**2+momenta(3,2)**2+momenta(3,3)**2))
     &         *180/pi
      thg2 = dacos(-momenta(4,3)/
     &         dSqrt(momenta(4,1)**2+momenta(4,2)**2+momenta(4,3)**2))
     &         *180/pi

      if (thg1 /= thg1) thg1 = 1
      if (thg2 /= thg2) thg2 = 1  ! If it is a nan, set to 1 (won't pass the cuts)

      g1_pass_cuts = ((thg1.ge.50).and.(thg1.le.130).and.
     &               (momenta(3,0).gt.0.02))
      g2_pass_cuts = ((thg2.ge.50).and.(thg2.le.130).and.
     &               (momenta(4,0).gt.0.02))

      g1_cuts = g1_pass_cuts
      g2_cuts = g2_pass_cuts
      g1_energy = g1_cuts * momenta(3,0)
      g2_energy = g2_cuts * momenta(4,0)

      if (g1_energy.gt.g2_energy) then
       eg = g1_energy * 1000
       thg = thg1
       mxxg = dSqrt((momenta(6,0) + momenta(7,0) + momenta(3,0))**2 -
     &       (momenta(6,1) + momenta(7,1) + momenta(3,1))**2 - 
     &       (momenta(6,2) + momenta(7,2) + momenta(3,2))**2 - 
     &       (momenta(6,3) + momenta(7,3) + momenta(3,3))**2) * 1000

      else
       eg = g2_energy * 1000
       thg = thg2
       mxxg = dSqrt((momenta(6,0) + momenta(7,0) + momenta(4,0))**2 -
     &       (momenta(6,1) + momenta(7,1) + momenta(4,1))**2 - 
     &       (momenta(6,2) + momenta(7,2) + momenta(4,2))**2 - 
     &       (momenta(6,3) + momenta(7,3) + momenta(4,3))**2) * 1000
      end if
      ! Save to variables in the same order as the requested histograms
      variables = (/thp, thm, pp, pm, pzp, pzm, ppp, ppm, mxx, xi, dphi,
     &              thav, thg, eg, mxxg, mtrk, mxxc, mtrkc/)

      ! Save to the corersponding histograms
      call distribute_variables(variables, i, n, value)
      return
      end
c ========================================================================
c --- Experimental cuts for KLOE-I scenario Strong2020
c ------------------------------------------------------------------------
      subroutine advanced_testcuts(accepted)
      include 'phokhara_10.0.inc'
      logical accepted, g1_pass_cuts, g2_pass_cuts
      real*8 thp, thm, ppp, ppm
      real*8 thg1, thg2, mxx
      
      ! Cut on th+
      thp = dacos(-momenta(6,3)/
     &         dSqrt(momenta(6,1)**2+momenta(6,2)**2+momenta(6,3)**2))
     &         *180.d0/pi
      accepted = (accepted.and.(thp.ge.50).and.(thp.le.130))

      if (.not.accepted) return
      ! Cut on th-
      thm = dacos(-momenta(7,3)/
     &         dSqrt(momenta(7,1)**2+momenta(7,2)**2+momenta(7,3)**2))
     &         *180.d0/pi
      accepted = (accepted.and.(thm.ge.50).and.(thm.le.130))
      if (.not.accepted) return

      ! Cut on pp+ and pz+
      ppp = dSqrt(momenta(6,1)**2 + momenta(6,2)**2)
      accepted = (accepted.and.((abs(momenta(6,3)).gt.0.09).or.
     &           (ppp.gt.0.16)))
      if (.not.accepted) return

      ! Cut on pp- and pz-
      ppm = dSqrt(momenta(7,1)**2 + momenta(7,2)**2)
      accepted = (accepted.and.((abs(momenta(7,3)).gt.0.09).or.
     &           (ppm.gt.0.16)))
      if (.not.accepted) return

      ! Cut on thg
      thg1 = dacos(-momenta(3,3)/
     &         dSqrt(momenta(3,1)**2+momenta(3,2)**2+momenta(3,3)**2))
     &         *180/pi
      thg2 = dacos(-momenta(4,3)/
     &         dSqrt(momenta(4,1)**2+momenta(4,2)**2+momenta(4,3)**2))
     &         *180/pi

      if (thg1 /= thg1) thg1 = 1
      if (thg2 /= thg2) thg2 = 1  ! If it is a nan, set to 1 (won't pass the cuts)

      g1_pass_cuts = ((thg1.ge.50).and.(thg1.le.130).and.
     &               (momenta(3,0).gt.0.02))
      g2_pass_cuts = ((thg2.ge.50).and.(thg2.le.130).and.
     &               (momenta(4,0).gt.0.02))
      
      accepted = (accepted.and.(g1_pass_cuts.or.g2_pass_cuts))
      if (.not.accepted) return

      ! Cut on mxx
      mxx =dSqrt((momenta(6,0) + momenta(7,0))**2 -
     &       (momenta(6,1) + momenta(7,1))**2 - 
     &       (momenta(6,2) + momenta(7,2))**2 - 
     &       (momenta(6,3) + momenta(7,3))**2)

      accepted = (accepted.and.(mxx**2.ge.0.1).and.(mxx**2.le.0.85))

      end 